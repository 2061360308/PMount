fuse_ptrs = {}  # key 为挂载设备名, value 为 FUSE 对象的指针， 用来在其他线程中关闭挂载
