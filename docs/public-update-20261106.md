# 2026-11-06 公开版更新

这次更新把近期已提交的核心实现同步到公开仓库，包括训练步验收、复数张量比较、
远端执行与容器化 trial、多任务 Harness、Benchmark v1 汇总和配套测试。

`trace` 现在要求先运行同一 trial 的 `verify`。未验证的请求返回不计 logical query 的
“请先运行 verify”；验证报告没有可定位的位置时不启动采集。聚焦采集在写入 NPZ 前估算
每端产物体积，超过 4 GiB 返回 `TRACE_TOO_LARGE`。

此次只同步核心代码、公开协议、复现脚本和测试。内部 `experiments/p2/` 的 trial 工作区、
原始报告、隐藏任务、oracle 和 evaluator secret 不在公开版中。旧 trial 的结论不因代码更新
而改变；新协议的 pilot 结果也不作为正式 Benchmark v1 成功率。
