`sorry for the chinese.`

页面功能
=======

列表页面
-------

0. quickform

    列表页面快速添加栏, 添加form根据model定义

0. acl

    基于条件的ACL权限
    ACL或选定用户时可以使用组概念

0. relate

    [已完成] 显示相关信息的菜单，到另一个页面后再页面显示主信息，添加时预填写改信息，填写后返回该页面。(关联父类别数据如何显示是一个问题)

0. editer

    [已完成] 即时编辑
    
    > http://vitalets.github.com/bootstrap-editable/#newrecord
    
    > https://github.com/toastdriven/django-tastypie

0. chart

    [已完成] 简单图表功能(现成的图表组件)，可以制定列显示，可以划定x轴显示，可以多列显示
    
0. details

    [已完成] 数据详情页面，可以级联显示相关内容 (定制显示哪些列，还有字段名称显示)
    
    [不实现] 级联数据显示
    
    > https://github.com/toastdriven/django-tastypie
    
0. filter

    [已完成] 过滤器强化
    [不实现] 级联过滤

0. bookmark

    [已完成] 记录特性的筛选

0. export

    [已完成] 导出csv, xml功能

0. list
    
    [已完成] 显示列
    
    级联显示列

0. refresh

    [已完成] 列表定时刷新功能

0. order

    根据列编辑排序 (在分页情况下很难做排序，可以考虑单页内排序。排序时仅安装指定列order显示，不能有其他列order by)

编辑页面
-------

0. [已完成] 关联数据查询，选择。使用select2
0. [已完成] autocomplete功能
0. [已完成] 日期，时间组件.
0. [已完成] 关联数据添加，inline formsets
0. [已完成] 突出当前用户的概念，填写内容时可以指定特定字段必须为当前用户。
0. [已完成] 数据添加向导功能

全局功能
-------

0. user settings, 可以记录跟用户相关的系统配置，例如页面使用布局记录。

    [已完成] 首页管理， widget，添加到widget功能，widget定时刷新（使用现成的widget控件）

    [已完成] 图标附加

    [已完成] bookmark功能，能够收藏任意url，变成widget已经列表快速显示菜单

    权限增加查看权限。
    > http://hi.baidu.com/cnydpl/item/3ce58c162bcfd2413b176e09

0. [已完成] log记录数据变化细节，数据版本维护，json diff

    > https://github.com/etianen/django-reversion

0. [已完成] json admin view， 可以返回某个对象的信息，某个对象的某个字段信息，更新某个字段。

细节任务
=======

1. [已完成] 表单向导自定义需要优化，界面需要优化。
2. [已完成] 添加widget的表单向导未完成。
3. [已完成] 可以考虑做一个专门的detail util view 显示详请页面，inline的数据无法使用AdminView的plugins.
4. [已完成] 延伸概念，view是plugin的体现，所有很多时候需要view实例来完成一些显示，所以应该创建UtilAdminView的概念，方便adminview的使用。
5. 考虑http://www.ichartjs.com/集成


