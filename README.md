
<p align="center">
    <img src="res/logo/logo_256.png" alt="PMount Logo" width="100" height="100">
    <br>
    <h1 align="center">PMount</h1>
</p>
<p align="center" style="font-size: 16px; border-bottom: 1px solid #dee2e6;">
    Python开发的云盘挂载工具，轻量、易用、拓展性强
</p>
<p align="center">
    <a href="#"><img src="https://img.shields.io/badge/python-3.10-blue.svg" alt="Python"></a>
    <a href="#"><img src="https://img.shields.io/badge/platform-windows-green.svg" alt="Platform"></a>
    <a href="#"><img src="https://img.shields.io/badge/nuitka-0.6.17-orange.svg" alt="Nuitka"></a>
    <a href="#"><img src="https://img.shields.io/github/v/release/your-repo/your-project" alt="Latest Release"></a>
    <a href="#"><img src="https://img.shields.io/badge/License-GPLv3-blue?color=#4ec820" alt="License"></a>
</p>

## 什么是 PMount
PMount 是一个基于 Python 开发的云盘挂载工具，支持多种云盘，轻量、易用、拓展性强。
使用PMount，通过简单的几个步骤你就可以将云盘挂载到本地，通过Windows的资源管理器轻松地访问那些云上资源。

PMount的灵感来自于[AList](https://github.com/alist-org/alist),仿照AList的设计，PMount也支持通过添加新的drivers文件来支持新的云盘。
相比于那些使用WebDAV协议的云盘挂载工具，PMount提供的挂载系统不单单是网络云盘的目录映射，而是云盘目录加本地虚拟缓存目录的相互结合。
PMount内置了一个文件缓存系统，你可以自定义缓存目录和空间上限，在展示云盘文件时，PMount会自动优先展示缓存目录的对应文件，否则会显示指向网盘资源的超链接。

依赖于上述的模式，PMount打开那些常用的文件和浏览本地文件没有区别，它能将你从 1.下载文件->2.查看/修改文件->3.上传文件 的繁琐流程中解放出来。
让大容量的云盘资源更好的结合进入你的日常工作流程中。

## 特性
- 支持多种云盘，且易于拓展
- 运行内存占用低，可以常驻后台
- 简洁易用的UI界面，操作使用更容易

## 安装使用
### 下载安装WinFsp
PMount使用WinFsp来挂载云盘，所以在使用PMount之前，你需要先安装WinFsp。不必担心，WinFsp的安装包迷你到只有30Mb，是一个非常轻量的开源应用。
你可以在[WinFsp官网](https://winfsp.dev/rel/)或者[GitHub](https://github.com/winfsp/winfsp/releases)上下载最新的安装包。
### 下载安装PMount
PMount的安装包可以在[GitHub Release](#)

## 源码运行、编译
## 打包编译
***使用 nuitka***
```shell
python -m nuitka --standalone --include-data-dir=drivers=drivers --include-data-file=config/config.yml=config/config.yml --include-data-file=logo.ico=logo.ico --plugin-enable=pyside6 --lto=yes --windows-icon-from-ico=./logo.ico --output-filename=PMount.exe --output-dir=./output run.py
```

***编译qrc资源***
```shell
pyside6-rcc res/resource.qrc -o res/resource_rc.py
```
