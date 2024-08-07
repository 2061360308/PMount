
## BaseFileSystemOperations
### BaseFileSystemOperations 方法

#### get_volume_info
**解释：** 用于获取文件系统卷（Volume）的信息。
在 Windows 操作系统中，卷通常指的是逻辑驱动器，例如 C 盘、D 盘等。
在文件系统的上下文中，卷（Volume）是一个存储设备或存储设备的一部分，
它具有文件系统并且可以被操作系统挂载和访问。每个卷都有自己的文件系统结构、总大小、可用空间和卷标签（名称）。

**参数：** 无
**返回：** 要求返回一个dict类型的数据，具体字段如下：
- total_size :int  总空间大小，单位为字节
- free_size :int  可用空间，单位为字节
- volume_label :str  卷标签（名称）

```python
def get_volume_info(self) -> dict:
    """
    用于获取文件系统卷（Volume）的信息。
    在 Windows 操作系统中，卷通常指的是逻辑驱动器，例如 C 盘、D 盘等。
    在文件系统的上下文中，卷（Volume）是一个存储设备或存储设备的一部分，
    它具有文件系统并且可以被操作系统挂载和访问。每个卷都有自己的文件系统结构、总大小、可用空间和卷标签（名称）。
    
    @:return: dict
    Dict fields:
        - total_size :int  总空间大小，单位为字节
        - free_size :int  可用空间，单位为字节
        - volume_label :str  卷标签（名称）
    """
    raise NotImplementedError()
```

#### set_volume_label
**解释：** 用于设置卷标签（名称）。
**参数：** volume_label :str  卷标签（名称）
**返回：** 无
```python
def set_volume_label(self, volume_label: str) -> None:
    """
    设置卷标签
    @:param volume_label: str  卷标签（名称）
    @:return: None
    """
    raise NotImplementedError()
```

#### get_security_by_name
**解释：** 通过给定的file_name获取文件或目录的属性和安全描述符。
**参数：** file_name: str  文件或目录的名称
**返回：** 返回一个包含文件属性、安全描述符和安全描述符大小的元组。

(file_attributes: FILE_ATTRIBUTE, security_descriptor: SecurityDescriptor, security_descriptor_size: SecurityDescriptor.size)

其中`FILE_ATTRIBUTE`是`winfspy`定义的枚举类型
`SecurityDescriptor`是`winfspy.plumbing.security_descriptor.SecurityDescriptor`类。
有关`SecurityDescriptor`的信息请参考[SecurityDescriptor](#SecurityDescriptor)

```python
def get_security_by_name(self, file_name) -> Tuple[FILE_ATTRIBUTE, SecurityDescriptor, SecurityDescriptor.size]:
    """
    通过给定的file_name获取文件或目录的属性和安全描述符。
    
    @:param file_name: str  文件或目录的名称
    @:return: 返回一个包含文件属性、安全描述符和安全描述符大小的元组。
    (file_attributes, security_descriptor, security_descriptor_size)
    
    Returns: (file_attributes, security_descriptor, security_descriptor_size)
    """
    raise NotImplementedError()
```
#### create
**解释：** 用于创建文件或目录。
**参数：** file_name: str  文件或目录的名称

```python
def create(
    self,
    file_name,
    create_options,
    granted_access,
    file_attributes,
    security_descriptor,
    allocation_size,
) -> BaseFileContext:
    raise NotImplementedError()
```

## SecurityDescriptor
> 该类用于表示Windows安全描述符，Windows安全描述符包含了文件或目录的安全信息。

SecurityDescriptor主要类属性有handle，和size。handle：指向转换后的安全描述符的指针。size：安全描述符的大小。
```python
class SecurityDescriptor(NamedTuple):

    handle: Any
    size: int
```

### SecurityDescriptor 方法

#### from_cpointer
**解释：** 通过给定的C指针创建一个SecurityDescriptor对象。

**参数：** handle: Any  指向安全描述符的C指针

**返回：** 返回一个SecurityDescriptor对象
```python
@classmethod
def from_cpointer(cls, handle):
    if handle == ffi.NULL:
        return cls(ffi.NULL, 0)
    size = lib.GetSecurityDescriptorLength(handle)
    pointer = lib.malloc(size)
    new_handle = ffi.cast("SECURITY_DESCRIPTOR*", pointer)
    ffi.memmove(new_handle, handle, size)
    return cls(new_handle, size)
```

#### from_string
**解释：** 通过给定的字符串创建一个SecurityDescriptor对象。

**参数：** string: str  安全描述符的字符串表示, 有关这个字符串的格式请参考[Security Descriptor String Format](https://learn.microsoft.com/zh-cn/windows/win32/secauthz/security-descriptor-string-format)

**返回：** 返回一个SecurityDescriptor对象
```python
@classmethod
def from_string(cls, string_format):
    # see https://learn.microsoft.com/zh-cn/windows/win32/secauthz/security-descriptor-string-format
    psd = ffi.new("SECURITY_DESCRIPTOR**")
    psd_size = ffi.new("ULONG*")
    if not lib.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        string_format, lib.WFSPY_STRING_SECURITY_DESCRIPTOR_REVISION, psd, psd_size
    ):
        raise RuntimeError(
            f"Cannot create security descriptor `{string_format}`: "
            f"{cook_ntstatus(lib.GetLastError())}"
        )
    return cls(psd[0], psd_size[0])
```

#### to_string
**解释：** 将SecurityDescriptor对象转换为字符串表示。

**参数：** 无

**返回：** 返回一个字符串表示的安全描述符，有关这个字符串的格式请参考[Security Descriptor String Format](https://learn.microsoft.com/zh-cn/windows/win32/secauthz/security-descriptor-string-format)
```python
def to_string(self):
    pwstr = ffi.new("PWSTR*")
    flags = (
        lib.WFSPY_OWNER_SECURITY_INFORMATION
        | lib.WFSPY_GROUP_SECURITY_INFORMATION
        | lib.WFSPY_DACL_SECURITY_INFORMATION
        | lib.WFSPY_SACL_SECURITY_INFORMATION
    )
    if not lib.ConvertSecurityDescriptorToStringSecurityDescriptorW(
        self.handle, lib.WFSPY_STRING_SECURITY_DESCRIPTOR_REVISION, flags, pwstr, ffi.NULL
    ):
        raise RuntimeError(
            f"Cannot convert the given security descriptor to string: "
            f"{cook_ntstatus(lib.GetLastError())}"
        )
    result = ffi.string(pwstr[0])
    lib.LocalFree(pwstr[0])
    return result
```