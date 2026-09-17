mobile-ep — 客户端工程效能技能集

安装：
/plugin marketplace add git@git.bilibili.co:ai-marketplace/client.git
/plugin install mobile-ep

升级：
/plugin marketplace update client
/reload-skills

主技能：
ci-failure-analyzer ：贴任意 pipeline / job / MR 链接就能取日志、逐个失败 job 判端、派发到对应平台诊断并聚合结论，大仓一条 pipeline 同时挂 Android 和 iOS 也能分别处理。

gitlab-mr ：创建和 approve GitLab MR，自动推断项目、source branch、assignee 并从 commit 或分支名生成标题，fix 开头的分支会主动确认 target branch。

buildbuddy-perf-analyzer ：贴 buildbuddy url，进行单次构建的耗时分析，给出构建阶段耗时拆解、最慢 target TOP N 和缓存命中率。

bazel-registry-publish ：把 Bazel Module 发布到内部 BCR，会先查仓库可见性决定走 tag 模式还是上传模式。

git-weekly-report ：跨仓库拉本人提交生成中文周报/日报/月报，同时按 author 和 AI-Code-Operator: 尾行归属，不会漏掉 author 为 AiCoding 的 AI 协作产出。

仓库路径：
https://git.bilibili.co/ai-marketplace/client/-/tree/main/plugins/mobile-ep
有需求/兴趣的同学也可以直接改或者加技能