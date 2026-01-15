<img width="1404" height="970" alt="image" src="https://github.com/user-attachments/assets/43972743-adb8-4240-b2b9-09d05021f02a" /># UNF 贴图工具集

这是一个使用 Python 和 PyQt5 开发的桌面小工具集，旨在帮助游戏开发者或美术师快速、灵活地处理贴图的 RGBA 通道。项目包含三个独立的脚本，提供了两种核心功能：**通道调整与拆分** 和 **通道合并**。

## 工具介绍

此项目包含三个脚本文件，您可以根据需要选择运行：

1.  **`UNF Texture Tool1.py` - 通道调整与拆分器 (Adjuster & Splitter)**
    -   **核心功能**: 专注于处理**单个**源贴图。您可以对它的 RGBA 通道进行精细调整，并将结果自由组合成任意数量的输出贴图。
    -   **主要特性**:
        -   拖拽式通道映射，直观地将源通道（R/G/B/A）分配给目标通道。
        -   实时调整每个输出通道的**亮度**和**对比度**。
        -   可为任意通道填充纯色（例如，为Alpha通道填充纯白）。
        -   支持创建多个输出方案，一次操作即可从单个源文件导出多张不同的贴图。
        -   提供“一键分离 RGBA”和“法线贴图”等快捷模式。
        -   支持对整个文件夹的图片应用当前配置进行批量处理。

2.  **`UNF Texture Tool2.py` - 通道合并器 (Packer)**
    -   **核心功能**: 专注于将**多个**独立的贴图文件（通常是灰度图）合并（Packing）到一张贴图的不同通道中。这在 PBR 流程中非常实用，例如将金属度（Metallic）、粗糙度（Roughness）、环境光遮蔽（AO）合并为一张贴图。
    -   **主要特性**:
        -   通过文件库管理所有待处理的源文件。
        -   强大的批处理模式，通过文件名后缀（如 `_m`, `_r`, `_ao`）自动识别并分组文件。
        -   为每个目标通道（R/G/B/A）分别指定源文件后缀和源通道。
        -   可以为未指定文件的通道填充纯色。
        -   自动根据分组生成最终的合并贴图。

3.  **`UNF Texture Tool2in1.py` - 二合一整合版**
    -   **核心功能**: 将上述两种工具整合到一个应用程序中，并提供了更现代化、统一的用户界面。您可以在 "Adjuster"（调整器）和 "Packer"（合并器）两个模式之间自由切换。
    -   该版本不是很好用，推荐根据功能运行两个独立的脚本。

## 程序教程
<img width="1404" height="970" alt="组 1" src="https://github.com/user-attachments/assets/5510fdb7-9558-47c6-806b-52eb48c5861e" />
<img width="1404" height="970" alt="组 2" src="https://github.com/user-attachments/assets/a5dd2c3e-c2fa-4c43-853e-d1a0469c051c" />
<img width="1404" height="970" alt="组 3" src="https://github.com/user-attachments/assets/9300e6c9-a4db-44c9-ad27-badc546b1651" />
<img width="1404" height="950" alt="组 4" src="https://github.com/user-attachments/assets/ba76860e-0ea2-49c1-b150-140b106df86e" />
<img width="1204" height="847" alt="R组 1" src="https://github.com/user-attachments/assets/67ca73af-365d-4d9f-b7b4-4a565dac9b9b" />
<img width="1204" height="847" alt="R组 2" src="https://github.com/user-attachments/assets/fa333fc1-3b6c-4bb1-9c29-50e357747c44" />
<img width="1204" height="847" alt="R组 3" src="https://github.com/user-attachments/assets/63609634-9288-4325-8c2a-7d20e819929b" />
<img width="1204" height="847" alt="R组 4" src="https://github.com/user-attachments/assets/70482e10-513a-4d6d-89d3-7bfaef38d235" />
<img width="1204" height="847" alt="R组 5" src="https://github.com/user-attachments/assets/77756af7-b219-4ea8-b8d7-79fe15ee5434" />
<img width="1404" height="970" alt="normal" src="https://github.com/user-attachments/assets/e8bddfdc-1d38-4548-bce5-5a91baa39ea9" />
<img width="1404" height="970" alt="RGBA" src="https://github.com/user-attachments/assets/2fd18868-b930-43ec-ad86-5b3d05662a24" />
    增加序号前缀/Export文件夹
    勾选后将会给输出按照顺序增加从1开始的前缀，比如Texture.png咱找Out配置输出就会输出Texture_1_Out.png


## 程序说明
若在使用中发现 Bug 或有功能建议，欢迎提交 Issue 或 Pull Request。
虽然但是，因为整篇都是ai写的，我没有能力很好的修复，只能尽力而为了。
