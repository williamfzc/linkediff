# 已废弃

该项目转由 opensibyl 社区统一继续开发。

https://github.com/opensibyl

---

# Linke (D) iff

linked graph for diff

## 背景与效果

在研发流程中无论是 code review、MR 基本都绕不开 code diff 的存在，而人眼很难准确评估 diff 的影响规模。

![](https://i.postimg.cc/L5cwt7qS/Wechat-IMG8.jpg)

linkediff 可以在无需编译的情况下对你的代码进行解析，指出diff的影响范围：

![](https://i.postimg.cc/sX0tX1sv/Wechat-IMG9.jpg)

通过脑图可以看到：

- 对 UTGen.java 发生了三块变更
- 64-216行这块影响了 methodsToCases 方法
- 这个方法调用了近40个方法，并被2个方法调用

他同时也生成易处理的JSON文件便于与其他系统（如CI）配合。

```json5
{
  "sibyl-core/src/main/java/com/williamfzc/sibyl/core/listener/java8/Java8MethodListener.java": [
    {
      "start": 9,
      "end": 15,
      "affected_functions": [
        {
          "Name": "enterClassDeclaration",
          "ReturnType": "void",
          "MultipleReturns": null,
          "Parameters": [
            {
              "Modifiers": null,
              "ParamName": "",
              "TypeValue": "ctx",
              "TypeType": "Java8Parser.ClassDeclarationContext",
              "ReturnTypes": null,
              "Parameters": null
            }
          ],
          "FunctionCalls": [
            {
              "Package": "com.williamfzc.sibyl.core.listener",
              "Type": "chain",
              "NodeName": "Java8Parser.ClassDeclarationContext",
              "FunctionName": "normalClassDeclaration",
              "Parameters": null,
              "Position": {
                "StartLine": 55,
                "StartLinePosition": 20,
                "StopLine": 55,
                "StopLinePosition": 42
              }
            }
            ...
          ]
        }
        ...
      ]
    }
    ...
  ]
}
```

## 使用

当前只支持java项目。

### 进入你自己的工程

```bash
git clone https://github.com/jacoco/jacoco
cd jacoco
```

### 执行分析

#### 通过docker

```bash
docker run --rm -v `pwd`:/usr/src/app williamfzc/linkediff:v0.2.1 linkediff run
```

#### 常规方式

你需要安装 Python3 及 [coca](https://github.com/modernizing/coca/releases/tag/v2.3.0)。

```bash
pip3 install linkediff
linkediff init
```

你会在你的项目目录下看到 `.linkediff.json` 配置文件，将其中 coca_cmd 指向 coca可执行文件 的路径即可。

```bash
linkediff run
```

### 结果

在运行完成后你可以看到一些结果文件，如 `ldresult.json`, `ldresult.xmind`。结合自身需要进一步处理即可。

> 由于xmind没有官方sdk，生成的xmind文件只能使用xmind8打开，详见 [#1](https://github.com/williamfzc/linkediff/issues/1) 。

### 如果依旧遇到困难

可以参考 github actions 中是如何做的：[传送门](./.github/workflows/python-package.yml)。

## contribution / design

智能diff功能存在我的TODO里很久了，之前的设计是：

- tree-sitter（这里选型有很多） 转 ast graph
- ast graph -> 更高层级的、通用 graph
- raw diff 生成
- 代入 graph 抠出整条调用上下游

而后来偶然发现了 [coca](https://github.com/modernizing/coca) ，发现已经将第二步与第四步完成了。所以趁着休息日摸鱼把这个最小可体验版本写（拼）出来了。

这个版本可能只会被用于验证价值与试水，如果有一定使用场景再考虑具体选型与适配。当前版本自由参与，结构也非常简单，欢迎PR但请不要花费太多时间。欢迎各类建议。

## performance

目前的性能不是理想状态，因为只是简单粘到一起。选型并没有真正定下来，所以暂时不会在性能上做过多优化。不过也处于一个能用的状态，基本满足CI的需求。

## refs

- [tree-sitter](https://github.com/tree-sitter/tree-sitter)
- [antlr4](https://github.com/antlr/antlr4)
- [sementic](https://github.com/github/semantic)
- [coca](https://github.com/modernizing/coca)

## license

[MIT](LICENSE)
