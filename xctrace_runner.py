import os
import subprocess
import shutil
import time
import sys
import signal
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import json
from data_visualizer import ParsedData, DataVisualizer


def main():
    Path("./temp/").mkdir(parents=True, exist_ok=True)
    Path("./temp/parse").mkdir(parents=True, exist_ok=True)
    Path("./temp/save").mkdir(parents=True, exist_ok=True)
    Path("./temp/visualize").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-template_path",
        help="xcode instrument template",
        default="./fps-cpu-mem.tracetemplate",
    )
    parser.add_argument(
        "-device_id",
        required=True,
        help="iPhone device_id",
        default="",
    )
    parser.add_argument(
        "-target_process_name",
        help="target analyse process",
        default="Steam",
    )
    parser.add_argument(
        "-time_limit",
        help="time_limit，<time[ms|s|m|h]>",
        default=None,
    )
    args = parser.parse_args()
    template_path = args.template_path
    device_id = args.device_id
    target_process_name = args.target_process_name
    time_limit = args.time_limit

    # record
    recorder = XCTraceRecorder(template_path=template_path, device_id=device_id)
    recorder.record(time_limit=time_limit)
    trace_path = recorder.output_trace_path

    # export
    trace_id = recorder.id
    log_path = f"./temp/parse/{trace_id}_parse.log"
    parser = XCTraceParser(trace_path, log_path, target_process_name, trace_id=trace_id)
    parser.parse()
    parser.save()

    # visualize
    print("开始可视化 Start visualize")
    html_path = f"./temp/visualize/{trace_id}_fps.html"
    trace_id = recorder.id
    fps_pd = XCTraceVisualizer(
        f"{trace_id} FPS",
        trace_id=trace_id,
        data_type=DataType.FPS,
        data_detail=parser.fps_values,
    ).transform_data()
    cpu_pd = XCTraceVisualizer(
        f"{trace_id} CPU",
        trace_id=trace_id,
        data_type=DataType.CPU,
        data_detail=parser.cpu_values,
    ).transform_data()
    mem_pd = XCTraceVisualizer(
        f"{trace_id} MEM",
        trace_id=trace_id,
        data_type=DataType.MEM,
        data_detail=parser.mem_values,
    ).transform_data()
    dv = DataVisualizer(html_path=html_path)
    dv.add_parsed_data(fps_pd)
    dv.add_parsed_data(cpu_pd)
    dv.add_parsed_data(mem_pd)
    dv.render_html()
    print(f"可视化完成 End visualize, render HTML path: {html_path}")


class XCTraceRecorder:
    """
    The encapsulation class for running record
    Only support 1 template, 1 device_id, 1 record task
    """

    def __init__(self, template_path, device_id):
        ct = int(time.time())
        random_id = get_random_id(4)
        self.id = f"{ct}_{random_id}"
        self.log_path = f"./temp/{self.id}_run.log"
        self.record_log_path = f"./temp/{self.id}_record.log"

        self.template_path = template_path
        self.device_id = device_id
        self.output_trace_path = f"./temp/{self.id}.trace"

    def print_log(self, strs):
        print(strs)
        with open(self.log_path, "a") as f:
            f.write(strs)
            f.write("\n")

    def record(self, time_limit=None):
        args_dict = {
            "template": self.template_path,
            "device": self.device_id,
            "output": self.output_trace_path,
        }
        if time_limit:
            args_dict["time-limit"] = time_limit
        args_list = "xcrun xctrace record --append-run --all-process".split(" ")
        for key, value in args_dict.items():
            args_list.append(f"--{key}")
            args_list.append(value)
        self.print_log(f"args_list: {args_list}")
        self.print_log(f"args_list join: {' '.join(args_list)}")

        rlog_fd = open(self.record_log_path, "a")
        proc = subprocess.Popen(
            args_list, stdout=rlog_fd, stderr=rlog_fd, universal_newlines=True
        )
        self.print_log(f"subprocess pid {proc.pid}")
        try:
            proc.wait()
        except KeyboardInterrupt as e:
            self.print_log(f"KeyboardInterrupt {e}, send SIGINT，wait `record` stop")
            proc.send_signal(signal.SIGINT)
            proc.wait()


class XCTraceParser:
    def __init__(self, trace_path, log_path, target_process_name, trace_id=None):
        if trace_id is None:
            ct = int(time.time())
            random_id = get_random_id(4)
            self.id = f"{ct}_{random_id}"
        else:
            self.id = trace_id
        self.trace_path = trace_path
        self.log_path = log_path
        self.temp_path = "./temp/parse"
        self.prefix_cmd = f"xcrun xctrace export --input {trace_path} "
        self.target_process_name = target_process_name

        self.fps_values = None
        self.cpu_values = None
        self.mem_values = None

    def print_log(self, strs):
        print(strs)
        with open(self.log_path, "a") as f:
            f.write(strs)
            f.write("\n")

    def parse(self):
        self.print_log("开始解析 Start parsing")

        self._get_root()
        fps_values = self._get_fps()
        cpu_values, mem_values = self._get_cpu_mem()
        # 原始数据是按时间倒序的
        # The raw data is in reverse chronological order
        self.fps_values = list(reversed(fps_values))
        self.cpu_values = list(reversed(cpu_values))
        self.mem_values = list(reversed(mem_values))

        self.print_log("解析完成 End parsing")

    def save(self, fps_path=None, cpu_path=None, mem_path=None, indent=2):
        self.print_log("开始保存 Start saving")

        if fps_path is None:
            fps_path = f"./temp/save/{self.id}_fps.json"
        if cpu_path is None:
            cpu_path = f"./temp/save/{self.id}_cpu.json"
        if mem_path is None:
            mem_path = f"./temp/save/{self.id}_mem.json"

        self.print_log(f"fps_path: {fps_path}")
        self.print_log(f"cpu_path: {cpu_path}")
        self.print_log(f"mem_path: {mem_path}")

        with open(fps_path, "w") as f:
            f.write(json.dumps(self.fps_values, indent=indent))
        with open(cpu_path, "w") as f:
            f.write(json.dumps(self.cpu_values, indent=indent))
        with open(mem_path, "w") as f:
            f.write(json.dumps(self.mem_values, indent=indent))

        self.print_log("保存完成 End saving")

    def _get_root(self):
        """
        解析 trace 文件，同时将解析日志输出到 log_path

        Parse the `trace` file and output the parsing log to `log_path`
        """

        self.print_log("GET root.xml")

        cmd = f"{self.prefix_cmd} --output {self.temp_path}/{self.id}_root.xml --toc"
        self.print_log(cmd)
        os.system(cmd)

    def _get_cache_ele(self, row, xpath, cache_map):
        """
        trace export 为了压缩数据，会给每条数据加 id，如果值一样则只加 ref
        本函数据此做了一些转换
        注意如果有多个结果，会返回第一个

        In order to compress data, `trace` `export` will add `id` to each data.
        If the value is the same, only `ref` will be added.
        The data in this function have been transformed.
        Note that if there are multiple results, the first one is returned.
        """
        eles = row.findall(xpath)
        first_ele = None
        for ele in eles:
            attrib = ele.attrib
            if attrib.get("id"):
                cache_map[attrib["id"]] = ele
            else:
                ele = cache_map[attrib["ref"]]
            if not first_ele:
                first_ele = ele
        return first_ele

    def _get_fps(self):
        self.print_log("GET fps")
        xml_path = f"{self.temp_path}/{self.id}_core-animation-fps-estimate.xml"
        cmd = (
            f"{self.prefix_cmd} --output {xml_path} "
            f'--xpath \'/trace-toc/run[@number="1"]/data/table[@schema="core-animation-fps-estimate"]\''
        )
        self.print_log(cmd)
        os.system(cmd)

        self.print_log("parse fps")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        rows = root.findall(".//*row")
        fps_values = []
        cm = {}
        for row in rows:
            st_fmt = self._get_cache_ele(row, ".//start-time", cm).attrib["fmt"]
            fps_text = self._get_cache_ele(row, ".//fps", cm).text
            fps_values.append({"fps": float(fps_text), "time": st_fmt})
        self.print_log(f"fps_values {fps_values}")

        return fps_values

    def _get_cpu_mem(self):
        self.print_log("GET cpu mem")
        xml_path = f"{self.temp_path}/{self.id}_sysmon-process.xml"
        cmd = (
            f"{self.prefix_cmd} --output {xml_path} "
            f'--xpath \'/trace-toc/run[@number="1"]/data/table[@schema="sysmon-process"]\''
        )
        self.print_log(cmd)
        os.system(cmd)

        target_process_name = self.target_process_name
        self.print_log(f"parse target process：{target_process_name} cpu mem")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        rows = root.findall(".//*row")
        cpu_values = []
        mem_values = []
        cm = {}
        cpu_text = None
        for _, row in enumerate(rows):
            # 缓存本节点下所有相关数据
            # Cache all relevant data under this node
            self._get_cache_ele(row, ".//size-in-bytes", cm)
            self._get_cache_ele(row, ".//system-cpu-percent", cm)

            st_fmt = self._get_cache_ele(row, ".//start-time", cm).attrib["fmt"]
            process_fmt = self._get_cache_ele(row, ".//process", cm).attrib["fmt"]
            if process_fmt.split(" ")[0] != self.target_process_name:
                continue
            # Unit：%
            # 可能会存在找不到该节点的情况，此时沿用上一次的值
            # There may be situations where the node cannot be found, and the last value is used
            cpu = self._get_cache_ele(row, ".//system-cpu-percent", cm)
            if cpu is not None:
                cpu_text = cpu.text
            cpu_values.append(
                {
                    "time": st_fmt,
                    "cpu": float(cpu_text),
                }
            )
            # 单位：bits，故转成 MB 需要 / 1024 / 1024
            # Unit: bits, so converting to MB requires / 1024 / 1024
            memory = self._get_cache_ele(row, ".//size-in-bytes[3]", cm).text
            # anonymous = self._get_cache_ele(row, ".//size-in-bytes[4]", cm).text
            # compressed = self._get_cache_ele(row, ".//size-in-bytes[5]", cm).text
            # purgeable = self._get_cache_ele(row, ".//size-in-bytes[6]", cm).text
            # real_private = self._get_cache_ele(row, ".//size-in-bytes[7]", cm).text
            # real_shared = self._get_cache_ele(row, ".//size-in-bytes[8]", cm).text
            resident_size = self._get_cache_ele(row, ".//size-in-bytes[9]", cm).text
            mem_values.append(
                {
                    "time": st_fmt,
                    "memory": float(memory) / 1024 / 1024,
                    "resident_size": float(resident_size) / 1024 / 1024,
                }
            )
        self.print_log(f"cpu_values {cpu_values}")
        self.print_log(f"mem_values {mem_values}")

        return cpu_values, mem_values


class DataType:
    FPS = 0
    CPU = 1
    MEM = 2


def date2timestamp(date_str, format_str="%M:%S"):
    import time

    tss1 = date_str
    time_array = time.strptime(tss1, format_str)
    return int(time.mktime(time_array))


def timestamp2date(timestamp, format_str="%M:%S"):
    import time

    time_array = time.localtime(timestamp)
    date = time.strftime(format_str, time_array)
    return date


class XCTraceVisualizer:
    def __init__(self, title, trace_id, data_type: DataType, data_detail: list):
        self.title = title
        self.trace_id = trace_id
        self.data_type = data_type
        self.data_detail = data_detail

        self._y_label = None
        # list, {"time": "MM:SS", "value": number}
        self._t_data = None

    def transform_data(self):
        t = self.data_type
        if t == DataType.FPS:
            self._y_label = "FPS"
            self._t_data = self._transform_fps_data()
        elif t == DataType.CPU:
            self._y_label = "CPU"
            self._t_data = self._transform_cpu_data()
        elif t == DataType.MEM:
            self._y_label = "MEM"
            self._t_data = self._transform_mem_data()
        return self._get_dv_parsed_data()

    def _get_dv_parsed_data(self):
        y_seq = []
        x_seq = []
        for item in self._t_data:
            y_seq.append(item["value"])
            x_seq.append(item["time"])
        return ParsedData(
            title=self.title, y_label=self._y_label, y_seq=y_seq, x_seq=x_seq
        )

    def _transform_fps_data(self):
        d = []
        for item in self.data_detail:
            _time = item["time"]
            _value = item["fps"]
            ts = date2timestamp(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_cpu_data(self):
        d = []
        for item in self.data_detail:
            _time = item["time"]
            _value = round(item["cpu"], 2)
            ts = date2timestamp(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_mem_data(self):
        d = []
        for item in self.data_detail:
            _time = item["time"]
            _value = round(item["memory"], 2)
            ts = date2timestamp(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _remove_same_time_data(self, data):
        filter_data = []
        before_item = None
        for item in data:
            _time = item["time"]
            _value = item["value"]
            _date = timestamp2date(item["time"])
            if before_item:
                if before_item["time"] == _time:
                    filter_data[-1]["value"] = _value
                else:
                    filter_data.append({"time": _date, "value": _value})
            else:
                filter_data.append({"time": _date, "value": _value})
            before_item = item
        return filter_data


def get_random_id(length=8, seed="1234567890qwertyuiopasdfghjklzxcvbnm"):
    import random

    result = ""
    for _ in range(length):
        result += random.choice(seed)
    return result


if __name__ == "__main__":
    main()
