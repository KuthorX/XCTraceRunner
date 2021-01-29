# XCTraceRunner

[English README](./README_en.md)

> 这是一个 POC 脚本，仅供参考，可用于日常测试，不建议直接用于工程。

一个简单的原生 iOS 性能测试工具。

## 环境要求

XCode 12.0.1 + python 3.7

### 可视化

- 生成 html，需要安装 [requirements.txt](./requirements.txt) 下的包

- 生成图片，需要下载 [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/downloads)

## 如何使用

直接运行该脚本即可，最后会输出对应应用的性能数据（fps + cpu + mem）的 Json 。
可用 `python xctrace_runner.py -h` 获取帮助信息。

## 技术原理

XCode 12 以后， `xctrace` 新增了 `export` 程序，可以将 Instruments 录制的 `trace` 文件以 XML 形式导出。

可能是考虑到性能， `export` 导出时并没有完全将所有数据导出，需要开发者自行解析 XML ，并通过多次调用 `export` 程序，得到预期数据。

## 覆盖的 Instruments

由于每个 instrument 录制的数据都不一样，这里仅解析以下 => 左侧的录制数据，最终输出保存 => 右侧的数据：

- `Core Animation FPS` => fps
- `Activity Monitor` => cpu、mem、resident size

## 关于内存指标

通过半天搜集资料研究，基本可以得出 `sysmon-process`（从 Activity Monitor 获取） 的各个内存值大致含义如下

```txt
Memory == VSS
Anonymous Mem == Dirty？
Compressed Mem == iOS 7 之后的压缩内存技术
Purgeable Mem == Clean？
Real Private Mem == USS
Real Shared Mem == USS + 共享库内存
Resident Size == RSS
APP 实际使用内存 == Dirty + Compressed + Clean，实际计算发现比 VSS 大（为什么？）
```

经过实际比对，可得出 PerfDog 的 `Memory`、`RealMemory` 即为 `VSS`、`RSS`，故先提取这两种内存，有需要可自行修改使用 @_@

## 为什么做这个

1. XCode 11 及以前，苹果没有提供公开的 API 给开发者自行解析 trace 文件
2. 内部自动化测试使用了 [TraceUtility](https://github.com/Qusic/TraceUtility) 来获取 iOS 设备的性能数据
3. 日常测试时，使用到是 [PerfDog](https://perfdog.qq.com/)

而 XCode12 以后， `xctrace` 新增了 `export` 程序，可以将 Instruments 录制的 `trace` 文件以 XML 形式导出。

这给日常测试和自动化测试提供了一个崭新的思路 —— 于是，就有了这个工具 :)

## 优劣对比

本工具相对于 TraceUtility 和 PerfDog 有以下优势：

- 对比 TraceUtility
  1. 使用了苹果提供的官方工具，兼容性理论上更强
  2. 纯 Python 编写，对目前项目组人员来说更易于维护

- 对比 PerfDog
  1. 数据源更丰富，可自定义获取的数据更多
  2. 可直接用于目前项目组的自动化，灵活度更高

当然，也有一些劣势：

  1. 无法像 Instruments 和 PerfDog 那样实时绘制数据（但从目前项目组内的落地场景来看，这个劣势其实问题不大）
  2. 由于 `export` 是新程序，如果后续 `export` 输出的 XML 数据结构有大更新，则必须要人工更新解析逻辑（但该问题不一定会出现）

## 总结

事实上，正如一开始所说，这个脚本只是简单地使用了苹果官方提供的 `record` 和 `export` 而已。

所以，这个仅仅处于 POC 阶段的工具的真正价值，在于：提供了另一种收集 iOS 设备性能数据的思路，其能方便地用于各类自动化之中，进而提高研发效能，保障产品质量 ;)

## 主要参考资料

```txt
https://xta0.me/2012/07/10/iOS-Memory-1.html
https://www.cnblogs.com/decode1234/p/10298841.html
https://bbs.perfdog.qq.com/article-detail.html?id=5
```

## 扩展特性 / 后续 Todo

- 对于自动化测试 - 不考虑，原理很简单，根据实际工程应用相应逻辑即可