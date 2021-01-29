# XCTraceRunner

[中文文档](./README.md)

> This is a POC script. Recommended for daily test, not for automation test.

A simple vanilla iOS performance test tool.

## Env

XCode 12.0.1 + python 3.7

### Data Visualization

- Install pkg by [requirements.txt](./requirements.txt)

- If need snapshot, download [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/downloads)

## How to use

- Input: `python xctrace_runner.py -h` to get help info
- Output: some log, and finally you can get the fps/cpu/mem json data

## Principle

After Xcode 12, `xctrace` has a new `export` program, which can export XML data from `record` (usually record by `Instruments`).

But the export data is not complete - it requires developers parse XML by themselves (repeatly call `export`).

## Cover Instruments

Since each `instrument` has diffrent record data, this script only parse the following `instrument` data (left of `=>`), and output corresponding data (right of `=>`):

- `Core Animation FPS` => fps
- `Activity Monitor` => cpu、mem、resident size

## About Memory Index

Through research, we can basically get the following meanings of each memory value of sysmon-process (from `Activity Monitor` exported XML data):

```txt
Memory == VSS
Anonymous Mem == Dirty？
Compressed Mem == used after iOS 7 
Purgeable Mem == Clean？
Real Private Mem == USS
Real Shared Mem == USS + shared-memory
Resident Size == RSS
APP Use Memory(?) == Dirty + Compressed + Clean，but it's bigger than Memory mentioned above, after I calculated(why?)
```

After compared, 

After actual comparison, it can be concluded that `Memory` and `RealMemory` of [PerfDog](https://perfdog.qq.com/) are `VSS` and `RSS`. Therefore, this script only export this 2 kinds of memory. It can be modified if necessary @_@

## Why write this?

1. Before Xcode 12, Apple did not provide a public API for developers to parse trace files themselves
2. Our internal automation test uses [TraceUtility](https://github.com/Qusic/TraceUtility) to get the performance data of iOS devices
3. In daily testing, [PerfDog](https://perfdog.qq.com/) is used

After Xcode 12, `xctrace` has a new `export` program, which can export XML data from `record` (usually record by `Instruments`).

This provides a new way of thinking for daily testing and automated testing - so there's this tool :)

## Comparison of advantages and disadvantages

This tool has the following advantages over TraceUtility and PerfDog:

- Compare TraceUtility
  1. Using the official tools provided by Apple, the compatibility is stronger in theory
  2. Written in Python, it is easier to maintain for the current project team

- Compare PerfDog
  1. More abundant data sources, more data can be customized
  2. Can be directly used in the automation of the current project team, with higher flexibility

Of course, there are also some disadvantages：

  1. Unable to draw data in real time like Instruments and Perfdog (but judging from the landing scenarios in the current project team, this disadvantage is not a big problem)
  2. Because `export` is a newly released program, if the XML data structure exported by `export` is greatly updated, the parsing logic must be updated manually (but this problem does not necessarily occur)

## Sum up

In fact, as mentioned at the beginning, the script simply uses Apple's official tools `record` and `export`.

Therefore, the real value of the tool, which is only in the POC stage, IS that it provides another way to collect the performance data of iOS devices, which can be easily used in all kinds of automation, so as to improve the RD efficiency and ensure the product quality ;)

## Main references

```txt
https://xta0.me/2012/07/10/iOS-Memory-1.html
https://www.cnblogs.com/decode1234/p/10298841.html
https://bbs.perfdog.qq.com/article-detail.html?id=5
```

## Extended features / subsequent todo

- For automated testing - not considered, the principle is very simple. If necessary, the corresponding logic can be applied according to the actual project