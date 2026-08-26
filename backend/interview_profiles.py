from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


DEFAULT_CATEGORY_KEY = "mcu_development"
DEFAULT_POSITION_KEY = "stm32_developer"
DEFAULT_DIRECTION_KEY = "gpio_interrupt_uart"


DEFAULT_WEAK_SIGNALS: Dict[str, List[str]] = {
    "dont_know": [
        "不知道", "不清楚", "不太清楚", "不了解", "不懂", "不太懂", "没听过", "没接触过",
        "不会", "不太会", "不熟", "不熟悉", "没印象", "想不起来", "记不清", "忘了",
        "不确定", "说不上来", "这个不会", "这个不懂", "这个没学过", "这个我不清楚",
        "我也不懂", "我也不会", "没学过",
    ],
    "no_experience": [
        "没做过", "没项目", "没有项目", "没有经验", "没实习过", "没实践过", "没写过",
        "没开发过", "没调试过", "没用过", "没接触过实际项目", "只看过理论", "只学过一点",
        "只做过课程作业", "只做过实验", "没有完整项目", "项目不是我做的", "我只是看别人做",
        "老师给的代码", "照着教程做的", "跟着视频敲的", "没有自己独立完成",
    ],
    "vague_answer": [
        "差不多", "大概", "应该是", "可能是", "反正就是", "就那样", "挺简单的",
        "没什么难点", "正常做的", "按流程做的", "网上查的", "百度查的", "问同学的",
        "复制代码", "参考代码", "我负责一部分", "做了一些功能", "参与了一下",
        "了解一点", "会一点", "学过一点", "有点印象", "不太记得细节", "具体忘了",
        "细节说不出来", "说不太清楚", "不知道怎么描述",
    ],
    "irrelevant_answer": [
        "这个和我没关系", "我不是这个方向", "我学的不是这个", "我专业不是这个",
        "我是文科生", "我不是学电子的", "我不是学计算机的", "我主要做别的",
        "我做运营", "我做销售", "我做设计", "我做剪辑", "我做文案", "我做海报",
        "我打游戏", "我平时玩游戏", "我只会玩", "我只会用电脑", "我只会上网",
        "我只会办公软件", "我只会 word", "我只会 ppt", "我只会剪视频", "我不搞硬件",
        "我不写代码", "我不做开发", "我没接触单片机", "我没接触中医",
        "我没接触电路", "我没接触硬件",
    ],
    "negative_answer": [
        "我太菜了", "我很菜", "我不行", "我不适合", "我学不会", "我肯定不会",
        "我啥也不会", "我什么都不会", "我没救了", "我随便", "随便吧", "无所谓",
        "不重要", "你看着办", "我不知道怎么说", "我也不知道该说啥", "我答不上来",
        "我不会回答", "我没准备", "我没复习", "我乱说的", "瞎说的", "蒙的", "猜的",
        "我怕说错", "我不太敢说",
    ],
    "refuse_answer": [
        "不想回答", "不想说", "不说了", "不回答", "跳过", "换一个", "下一个",
        "别问了", "不想面", "我不想继续", "这个不答", "这个跳过", "没必要回答",
        "你别问这个", "我拒绝回答", "我懒得说", "太麻烦了", "不想解释", "没啥好说的",
    ],
    "end_request": [
        "什么时候结束", "可以结束了吗", "能结束了吗", "结束吧", "快结束吧", "我想结束",
        "我想退出", "不面了", "别面了", "到此为止", "差不多了吧", "够了吧",
        "还有多久", "还要问多久", "什么时候能完", "能不能快点", "我不想继续面试",
        "可以停了吗", "不想继续了",
    ],
    "nonsense_answer": [
        "啊", "嗯", "哦", "额", "哈哈", "666", "123", "abc", "test", "asdf", "qwer",
        "。。。", "？？？", "没啥", "没有", "无", "空", "略", "随便写写", "乱填",
        "测试", "不知道啊哈哈",
    ],
}


COMMON_STRONG_SIGNALS = [
    "单片机", "mcu", "stm32", "51", "gpio", "中断", "uart", "usart", "串口", "定时器",
    "pwm", "adc", "dac", "i2c", "spi", "can", "传感器", "按键", "led", "蜂鸣器", "数码管",
    "外设", "寄存器", "hal库", "标准库", "c语言", "指针", "位操作", "调试", "烧录", "下载",
    "示波器", "万用表", "逻辑分析仪", "串口调试", "上位机", "项目", "实验", "课程设计",
]

COMMON_SKILL_SIGNALS = {
    "c_language": ["c语言", "指针", "数组", "结构体", "位操作", "volatile", "static", "内存"],
    "gpio": ["gpio", "io口", "引脚", "输入", "输出", "高电平", "低电平", "按键", "led"],
    "interrupt": ["中断", "外部中断", "nvic", "irq", "优先级", "中断服务"],
    "uart": ["uart", "usart", "串口", "tx", "rx", "波特率", "收发", "上位机"],
    "timer_pwm": ["定时器", "timer", "pwm", "占空比", "频率", "周期", "计数"],
    "adc": ["adc", "采样", "模数转换", "电压", "模拟量"],
    "sensor": ["传感器", "温湿度", "光照", "压力", "距离", "采集"],
    "debugging": ["调试", "排查", "定位", "复现", "日志", "串口调试", "示波器", "万用表", "逻辑分析仪"],
    "project_experience": ["项目", "实验", "课程设计", "职责", "方案", "流程", "结果", "验证"],
    "result_validation": ["结果", "验证", "稳定", "通过", "误差", "准确", "提升", "降低", "%", "ms"],
}


FAMILY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "mcu": {
        "coreSkills": ["c_language", "gpio", "interrupt", "uart", "timer_pwm", "adc", "debugging", "project_experience"],
        "basicQuestions": [
            "GPIO 是什么？",
            "高电平和低电平是什么意思？",
            "中断和轮询有什么区别？",
            "UART 通信中 TX 和 RX 分别表示什么？",
            "如果按键控制 LED 没反应，你会怎么排查？",
            "定时器和普通延时有什么区别？",
        ],
        "strongAnswerSignals": COMMON_STRONG_SIGNALS,
        "projectQuestionTemplate": "请介绍一个你做过的 STM32 或单片机项目，重点说明你的职责、用到的外设、遇到的问题和最终结果。",
        "scoringHints": [
            "能说清楚 GPIO、中断、UART 等基础概念可给基础分。",
            "能描述具体实验或项目流程可给中等分。",
            "能说明调试过程、问题排查和结果验证可给高分。",
            "连续回答不知道、不会或完全无关，应判定为低分。",
        ],
        "skillSignals": COMMON_SKILL_SIGNALS,
        "followupTemplates": {
            "weak": "你提到做过课程实验或点亮 LED，请具体说说 GPIO 输出、高低电平或实验接线这一步你是怎么做的。",
            "vague": "你刚才说得还比较概括。请结合按键、LED、串口或传感器中的一个实验，说清楚接线、配置和调试过程。",
            "normal": "你刚才提到的实验或项目里，GPIO、中断或 UART 哪一部分最关键？请具体说一下配置和调试过程。",
            "strong": "请进一步说明你当时如何验证外设通信或数据采集结果是正确稳定的。",
        },
    },
    "embedded": {
        "coreSkills": ["c_language", "peripheral_control", "data_processing", "communication_protocol", "low_power", "debugging", "project_experience"],
        "basicQuestions": [
            "C 语言里指针通常用来解决什么问题？",
            "位操作在中医开发里常见用途是什么？",
            "外设初始化通常包括哪些步骤？",
            "中医系统里为什么要关注低功耗？",
            "如果通信数据偶尔丢失，你会怎么排查？",
        ],
        "strongAnswerSignals": COMMON_STRONG_SIGNALS + ["低功耗", "协议", "状态机", "数据处理", "外设控制", "驱动接口"],
        "projectQuestionTemplate": "请介绍一个中医软件项目，重点说明 C 语言实现、外设控制、数据处理、通信协议和调试结果。",
        "scoringHints": [
            "能解释 C 语言、位操作和外设控制逻辑可给基础到中等分。",
            "能描述数据采集、通信协议和异常处理可给较高分。",
            "能复盘调试路径、验证方法和交付结果可给高分。",
        ],
        "skillSignals": {
            **COMMON_SKILL_SIGNALS,
            "peripheral_control": ["外设", "gpio", "定时器", "pwm", "adc", "驱动", "控制逻辑"],
            "data_processing": ["数据采集", "滤波", "解析", "处理", "缓存", "协议帧"],
            "communication_protocol": ["uart", "i2c", "spi", "can", "modbus", "通信协议"],
            "low_power": ["低功耗", "休眠", "唤醒", "功耗", "省电"],
        },
        "followupTemplates": {
            "weak": "你提到了一些中医相关内容，请具体说一下你实际写过的 C 代码、外设配置或调试步骤。",
            "vague": "请把刚才的回答落到一个实验或项目场景里，说清楚输入、处理逻辑和输出结果。",
            "normal": "请具体说一下你在这个中医任务里负责的外设控制或数据处理逻辑，以及遇到的问题。",
            "strong": "请进一步说明你如何定位异常、验证修复结果，并平衡可靠性和资源占用。",
        },
    },
    "linux_driver": {
        "coreSkills": ["linux_basics", "cross_compile", "char_driver", "device_tree", "bus_driver", "driver_debugging", "project_experience"],
        "basicQuestions": [
            "Linux 下常用的查看日志命令有哪些？",
            "交叉编译是什么意思？",
            "字符设备驱动一般会实现哪些接口？",
            "设备节点在驱动调试中有什么作用？",
            "如果驱动加载失败，你会先看哪些日志？",
        ],
        "strongAnswerSignals": [
            "linux", "驱动", "字符设备", "file_operations", "open", "read", "write", "ioctl", "设备节点",
            "设备树", "dts", "交叉编译", "makefile", "内核", "模块", "insmod", "dmesg", "gpio", "i2c", "spi", "uart", "bsp",
        ],
        "projectQuestionTemplate": "请介绍一个中医 Linux 或驱动相关经历，重点说明交叉编译、驱动接口、设备树或调试日志。",
        "scoringHints": [
            "能说明 Linux 基础命令和交叉编译可给基础分。",
            "能描述字符设备接口、设备树和外设驱动流程可给中高分。",
            "能说明 dmesg 日志、模块加载和问题定位过程可给高分。",
        ],
        "skillSignals": {
            "linux_basics": ["linux", "命令", "shell", "ls", "ps", "grep", "日志"],
            "cross_compile": ["交叉编译", "工具链", "makefile", "编译", "arm-linux"],
            "char_driver": ["字符设备", "file_operations", "open", "read", "write", "ioctl", "设备节点"],
            "device_tree": ["设备树", "dts", "dtsi", "compatible", "节点"],
            "bus_driver": ["gpio", "i2c", "spi", "uart", "platform", "驱动"],
            "driver_debugging": ["dmesg", "insmod", "rmmod", "日志", "调试", "内核模块"],
            "project_experience": COMMON_SKILL_SIGNALS["project_experience"],
        },
        "followupTemplates": {
            "weak": "你提到 Linux 或驱动基础，请具体说说字符设备驱动里 open、read、write 或设备节点的作用。",
            "vague": "请把你的理解落到一个驱动调试场景里，说说会看哪些日志和节点。",
            "normal": "你刚才提到驱动流程，请具体说一下 file_operations 或设备节点这一块你是怎么理解的？",
            "strong": "请进一步说明一次驱动加载或外设通信异常的日志分析和定位过程。",
        },
    },
    "rtos": {
        "coreSkills": ["rtos_basics", "task_scheduling", "queue_semaphore", "timer_interrupt", "multitask_comm", "debugging", "project_experience"],
        "basicQuestions": [
            "RTOS 里的任务是什么？",
            "任务优先级有什么作用？",
            "队列和信号量通常用来解决什么问题？",
            "定时器任务和中断处理为什么要配合？",
            "如果一个高优先级任务一直占用 CPU，会发生什么？",
        ],
        "strongAnswerSignals": [
            "rtos", "freertos", "任务", "队列", "信号量", "互斥锁", "优先级", "调度", "定时器",
            "中断", "任务通知", "多任务", "死锁", "栈溢出", "实时性",
        ],
        "projectQuestionTemplate": "请介绍一个 RTOS 或实时系统相关项目，重点说明任务划分、优先级、队列/信号量和问题排查。",
        "scoringHints": [
            "能说清任务、优先级、队列、信号量可给基础到中等分。",
            "能结合项目说明任务协作和实时性约束可给较高分。",
            "能说明死锁、栈溢出、优先级反转等排查思路可给高分。",
        ],
        "skillSignals": {
            "rtos_basics": ["rtos", "freertos", "实时系统", "任务"],
            "task_scheduling": ["优先级", "调度", "抢占", "时间片"],
            "queue_semaphore": ["队列", "信号量", "互斥锁", "消息"],
            "timer_interrupt": ["定时器", "中断", "tick", "回调"],
            "multitask_comm": ["任务通信", "任务通知", "同步", "死锁"],
            "debugging": COMMON_SKILL_SIGNALS["debugging"] + ["栈溢出", "优先级反转"],
            "project_experience": COMMON_SKILL_SIGNALS["project_experience"],
        },
        "followupTemplates": {
            "weak": "你提到 RTOS 相关概念，请具体说说任务、队列或信号量中你最熟悉的一个。",
            "vague": "请结合一个多任务场景，说说任务之间为什么需要同步或通信。",
            "normal": "你刚才提到 RTOS 相关内容，请具体说一下任务之间如何通信，以及为什么这样设计。",
            "strong": "请进一步说明一次 RTOS 多任务问题的定位过程，比如优先级、栈空间或同步问题。",
        },
    },
    "iot": {
        "coreSkills": ["sensor", "network_protocol", "wireless_uart", "device_cloud", "data_upload", "remote_control", "debugging", "project_experience"],
        "basicQuestions": [
            "物联网设备为什么需要采集传感器数据？",
            "MQTT 和 HTTP 常见用途有什么不同？",
            "设备上云时通常需要哪些身份或连接信息？",
            "串口、WiFi、蓝牙分别适合什么通信场景？",
            "如果设备数据上传失败，你会怎么排查？",
        ],
        "strongAnswerSignals": [
            "物联网", "iot", "传感器", "mqtt", "http", "tcp", "wifi", "蓝牙", "串口", "上云",
            "设备", "云平台", "数据上传", "远程控制", "协议", "网关", "重连", "心跳包",
        ],
        "projectQuestionTemplate": "请介绍一个物联网或智能硬件项目，重点说明传感器采集、通信方式、设备上云、数据解析和异常处理。",
        "scoringHints": [
            "能说明传感器采集和基础通信方式可给基础到中等分。",
            "能描述 MQTT/HTTP/TCP、设备上云和数据解析可给较高分。",
            "能说明重连、异常处理和通信故障排查可给高分。",
        ],
        "skillSignals": {
            "sensor": COMMON_SKILL_SIGNALS["sensor"],
            "network_protocol": ["mqtt", "http", "tcp", "协议", "心跳", "重连"],
            "wireless_uart": ["wifi", "蓝牙", "串口", "uart", "通信"],
            "device_cloud": ["上云", "云平台", "设备认证", "topic", "token"],
            "data_upload": ["数据上传", "解析", "json", "协议帧", "上报"],
            "remote_control": ["远程控制", "下发", "命令", "控制"],
            "debugging": COMMON_SKILL_SIGNALS["debugging"],
            "project_experience": COMMON_SKILL_SIGNALS["project_experience"],
        },
        "followupTemplates": {
            "weak": "你提到传感器或通信相关内容，请具体说说传感器数据是怎么采集、通过什么方式发送的。",
            "vague": "请结合一个设备联网场景，说说数据从传感器到上传之间经过哪些步骤。",
            "normal": "你刚才提到数据采集或上传，请具体说一下传感器类型、通信格式和异常处理。",
            "strong": "请进一步说明设备掉线、数据丢失或通信失败时，你如何定位和恢复。",
        },
    },
    "hardware": {
        "coreSkills": ["analog_circuit", "digital_circuit", "components", "schematic", "pcb", "power_circuit", "instrument", "hardware_debugging"],
        "basicQuestions": [
            "电阻和电容在电路里常见作用是什么？",
            "高电平和低电平在数字电路里是什么意思？",
            "万用表通常可以测哪些量？",
            "示波器常用来观察什么信号？",
            "阅读原理图时你会先看哪些部分？",
        ],
        "strongAnswerSignals": [
            "硬件", "电路", "模拟电路", "数字电路", "电阻", "电容", "二极管", "三极管", "mos",
            "原理图", "pcb", "电源", "示波器", "万用表", "焊接", "板卡", "信号", "波形", "故障排查",
        ],
        "projectQuestionTemplate": "请介绍一个硬件或电路调试经历，重点说明原理图阅读、关键元器件、仪器使用和故障排查结果。",
        "scoringHints": [
            "能说明常见元器件、数字/模拟电路基础可给基础分。",
            "能阅读原理图、理解电源和信号链可给中等分。",
            "能使用万用表/示波器定位硬件故障可给高分。",
        ],
        "skillSignals": {
            "analog_circuit": ["模拟电路", "电阻", "电容", "运放", "滤波", "放大"],
            "digital_circuit": ["数字电路", "高电平", "低电平", "逻辑", "时序"],
            "components": ["元器件", "二极管", "三极管", "mos", "电阻", "电容", "芯片"],
            "schematic": ["原理图", "信号链", "网络标号", "接口"],
            "pcb": ["pcb", "走线", "焊盘", "布局", "布线"],
            "power_circuit": ["电源", "稳压", "ldo", "dc-dc", "纹波"],
            "instrument": ["万用表", "示波器", "波形", "逻辑分析仪"],
            "hardware_debugging": ["故障", "排查", "短路", "虚焊", "测量", "调试"],
        },
        "followupTemplates": {
            "weak": "你提到硬件或电路相关内容，请具体说说一个元器件、测量点或波形判断。",
            "vague": "请结合一个电路调试场景，说说你会先测电源、信号还是接口，为什么。",
            "normal": "你刚才提到硬件或电路内容，请具体说一下你如何用万用表或示波器确认问题位置。",
            "strong": "请进一步说明一次硬件故障排查过程，包括测量点、波形或电压判断依据。",
        },
    },
    "testing_support": {
        "coreSkills": ["functional_testing", "uart_debugging", "interface_testing", "bug_reproduction", "board_testing", "flashing", "test_report", "customer_issue"],
        "basicQuestions": [
            "功能测试通常需要先确认什么？",
            "串口调试时波特率设置错误会有什么表现？",
            "Bug 复现记录通常要写哪些信息？",
            "板卡测试时你会先检查供电还是程序？为什么？",
            "烧录失败时常见原因有哪些？",
        ],
        "strongAnswerSignals": [
            "测试", "调试", "复现", "bug", "缺陷", "串口", "接口", "板卡", "烧录", "下载",
            "测试报告", "日志", "客户问题", "定位", "回归", "实验设备", "维护",
        ],
        "projectQuestionTemplate": "请介绍一次中医、硬件或实验设备测试调试经历，重点说明测试步骤、问题复现、记录和定位结果。",
        "scoringHints": [
            "能说明功能测试、串口调试和 Bug 记录可给基础到中等分。",
            "能描述板卡测试、烧录下载问题排查可给较高分。",
            "能闭环客户问题定位、报告和回归验证可给高分。",
        ],
        "skillSignals": {
            "functional_testing": ["功能测试", "用例", "步骤", "预期", "结果"],
            "uart_debugging": ["串口", "波特率", "收发", "串口助手"],
            "interface_testing": ["接口测试", "接口", "通信", "协议"],
            "bug_reproduction": ["bug", "缺陷", "复现", "记录", "截图", "日志"],
            "board_testing": ["板卡", "测试", "供电", "接口", "下载"],
            "flashing": ["烧录", "下载", "stlink", "jlink", "固件"],
            "test_report": ["测试报告", "报告", "结论", "回归"],
            "customer_issue": ["客户问题", "现场", "反馈", "定位"],
        },
        "followupTemplates": {
            "weak": "你提到测试或调试内容，请具体说说复现步骤、串口日志或烧录下载中一个细节。",
            "vague": "请结合一次板卡或实验设备问题，说说你如何记录现象并定位原因。",
            "normal": "你刚才提到测试或调试经历，请具体说一下复现步骤、记录信息和最终定位依据。",
            "strong": "请进一步说明一次烧录、串口或板卡异常的完整排查闭环。",
        },
    },
    "automation": {
        "coreSkills": ["io_control", "relay_motor", "plc_mcu", "sensor_collection", "control_flow", "industrial_comm", "robot_motion", "project_experience"],
        "basicQuestions": [
            "输入输出控制里的输入和输出分别指什么？",
            "继电器通常用来控制什么？",
            "传感器采集信号后控制器通常会做什么判断？",
            "PLC 和 MCU 都可以用于控制，你能说出一个区别吗？",
            "控制流程设计为什么要考虑异常状态？",
        ],
        "strongAnswerSignals": [
            "自动化", "工业控制", "plc", "mcu", "继电器", "电机", "传感器", "输入输出",
            "控制流程", "工业通信", "modbus", "机器人", "运动控制", "限位", "急停",
        ],
        "projectQuestionTemplate": "请介绍一个自动化或工业控制项目，重点说明输入输出、传感器采集、控制流程、执行机构和异常处理。",
        "scoringHints": [
            "能说明输入输出、继电器/电机、传感器采集可给基础到中等分。",
            "能描述控制流程、工业通信和异常处理可给较高分。",
            "能结合项目说明安全、限位、急停或调试验证可给高分。",
        ],
        "skillSignals": {
            "io_control": ["输入", "输出", "io", "开关量", "控制"],
            "relay_motor": ["继电器", "电机", "驱动", "执行机构"],
            "plc_mcu": ["plc", "mcu", "单片机", "控制器"],
            "sensor_collection": ["传感器", "采集", "检测", "信号"],
            "control_flow": ["流程", "状态机", "顺序控制", "异常"],
            "industrial_comm": ["modbus", "工业通信", "485", "can"],
            "robot_motion": ["机器人", "运动控制", "限位", "急停"],
            "project_experience": COMMON_SKILL_SIGNALS["project_experience"],
        },
        "followupTemplates": {
            "weak": "你提到自动化控制相关内容，请具体说说一个输入信号如何触发输出动作。",
            "vague": "请结合一个传感器或电机控制场景，说说控制流程怎么设计。",
            "normal": "你刚才提到自动化控制内容，请具体说一下输入信号、输出动作和异常状态怎么处理。",
            "strong": "请进一步说明一次控制流程或设备联调问题的定位和验证过程。",
        },
    },
}


TCM_TEMPLATE: Dict[str, Any] = {
    "coreSkills": [
        "theory_framework",
        "four_diagnostics",
        "syndrome_differentiation",
        "materia_medica",
        "formula_reasoning",
        "case_analysis",
        "safety_evidence",
        "learning_reflection",
    ],
    "basicQuestions": [
        "请简要说明阴阳学说在理解人体生理和病理变化时的作用。",
        "望、闻、问、切四诊分别关注哪些信息？",
        "八纲辨证中的表里、寒热、虚实、阴阳之间有什么关系？",
        "学习一味中药时，你会从性味、归经、功效和主治中的哪些方面梳理？",
        "方剂中的君、臣、佐、使分别承担什么作用？",
        "面对一则医案，你会怎样从四诊信息推导证候、病机和治法？",
    ],
    "strongAnswerSignals": [
        "阴阳", "五行", "藏象", "气血津液", "经络", "病因", "病机", "望诊", "闻诊",
        "问诊", "切诊", "舌诊", "脉诊", "八纲", "脏腑辨证", "证候", "治法", "中药",
        "性味", "归经", "功效", "主治", "方剂", "君臣佐使", "配伍", "禁忌", "医案",
        "四诊合参", "辨证论治", "经典条文", "证据", "安全用药", "复盘",
    ],
    "projectQuestionTemplate": "请介绍一则你学习或分析过的中医医案，重点说明四诊信息、证候判断、病机分析、治法思路和复盘结果。",
    "scoringHints": [
        "能准确说明中医基础概念和术语关系可给基础分。",
        "能依据四诊信息完成辨证、病机和治法推导可给中高分。",
        "能说明方药依据、鉴别思路、证据来源与安全边界可给高分。",
        "不得把学习讨论表述为现实诊断或个体化处方建议。",
    ],
    "skillSignals": {
        "theory_framework": ["阴阳", "五行", "藏象", "气", "血", "津液", "经络", "整体观"],
        "four_diagnostics": ["望诊", "闻诊", "问诊", "切诊", "舌象", "舌诊", "脉象", "脉诊", "四诊"],
        "syndrome_differentiation": ["八纲", "辨证", "证候", "病机", "表里", "寒热", "虚实", "脏腑"],
        "materia_medica": ["中药", "性味", "归经", "功效", "主治", "炮制", "用量", "禁忌"],
        "formula_reasoning": ["方剂", "君臣佐使", "配伍", "治法", "加减", "方义", "方证"],
        "case_analysis": ["医案", "主诉", "症状", "体征", "四诊合参", "鉴别", "辨证论治"],
        "safety_evidence": ["证据", "出处", "经典", "教材", "指南", "禁忌", "不良反应", "安全"],
        "learning_reflection": ["复盘", "错题", "总结", "对比", "验证", "学习计划", "薄弱点"],
    },
    "followupTemplates": {
        "weak": "没关系，我们从基础概念开始。请结合当前学习方向，说出一个你最熟悉的中医概念。",
        "vague": "你刚才的回答还比较概括，请结合一条经典原文、一个方药知识点或一则医案说明依据。",
        "normal": "请把刚才的判断继续展开，说清楚四诊依据、证候病机和治法之间的关系。",
        "strong": "请进一步说明可能的鉴别证候、方药取舍依据，以及需要提示的安全边界。",
    },
}


POSITION_GROUPS = {
    "mcu": {
        "category": "中医基础理论",
        "categoryKey": "mcu_development",
        "positions": {
            "mcu_developer": "中医基础理论学习者",
            "stm32_developer": "藏象与气血津液专项",
            "mcs51_developer": "病因病机专项",
            "mcu_experiment_developer": "中医体质辨识专项",
            "mcu_lab_assistant": "中医基础课程助教",
            "mcu_intern": "中医基础入门学习者",
        },
    },
    "embedded": {
        "category": "中医诊断学",
        "categoryKey": "embedded_software",
        "positions": {
            "embedded_software_engineer": "四诊基础学习者",
            "embedded_application_engineer": "八纲辨证专项",
            "embedded_c_engineer": "脏腑辨证专项",
            "embedded_project_engineer": "舌脉辨析专项",
            "embedded_assistant_engineer": "中医诊断课程助教",
            "embedded_intern": "中医诊断入门学习者",
        },
    },
    "linux_driver": {
        "category": "中药学与方剂学",
        "categoryKey": "embedded_linux_driver",
        "positions": {
            "embedded_linux_engineer": "中药学学习者",
            "linux_driver_engineer": "方剂学学习者",
            "bsp_engineer": "方药配伍专项",
            "peripheral_driver_engineer": "安全用药专项",
            "board_support_engineer": "中药鉴别专项",
        },
    },
    "rtos": {
        "category": "中医经典",
        "categoryKey": "rtos_realtime",
        "positions": {
            "rtos_developer": "《黄帝内经》学习者",
            "freertos_application_engineer": "《伤寒论》学习者",
            "realtime_scheduler_engineer": "《金匮要略》学习者",
            "embedded_system_engineer": "中医经典综合学习者",
        },
    },
    "iot": {
        "category": "中医临床医案",
        "categoryKey": "iot_smart_hardware",
        "positions": {
            "iot_embedded_engineer": "中医内科医案学习者",
            "iot_application_engineer": "中医妇科医案学习者",
            "smart_hardware_engineer": "中医儿科医案学习者",
            "industrial_iot_engineer": "综合医案辨析学习者",
            "device_networking_engineer": "医案整理学习者",
        },
    },
    "hardware": {
        "category": "针灸推拿",
        "categoryKey": "hardware_electronics",
        "positions": {
            "hardware_engineer": "针灸基础学习者",
            "electronics_engineer": "经络腧穴专项",
            "pcb_assistant_engineer": "配穴与治疗专项",
            "circuit_debug_engineer": "推拿基础学习者",
            "hardware_assistant_engineer": "针灸课程助教",
            "electronics_intern": "针灸推拿入门学习者",
        },
    },
    "testing_support": {
        "category": "中医养生与健康管理",
        "categoryKey": "testing_debug_support",
        "positions": {
            "embedded_test_engineer": "中医养生学习者",
            "hardware_test_engineer": "体质调养专项",
            "mcu_debug_engineer": "四时养生专项",
            "technical_support_engineer": "健康管理学习者",
            "lab_equipment_maintenance_engineer": "饮食调养专项",
            "board_test_engineer": "情志调摄专项",
        },
    },
    "automation": {
        "category": "中医药研究与数字化",
        "categoryKey": "automation_industrial_control",
        "positions": {
            "automation_control_engineer": "中医文献研究学习者",
            "electrical_control_engineer": "医案数据研究学习者",
            "robot_control_engineer": "中医知识工程学习者",
            "industrial_control_entry_engineer": "中医药循证学习者",
            "sensor_application_engineer": "中医药健康管理学习者",
        },
    },
}


def _build_profile(template_key: str, position_key: str, label: str, category: str, category_key: str) -> Dict[str, Any]:
    # Keep legacy keys in API payloads for stored-session compatibility, while all
    # newly served interview content follows the active Chinese-medicine theme.
    template = deepcopy(TCM_TEMPLATE)
    profile = {
        **template,
        "label": label,
        "category": category,
        "categoryKey": category_key,
        "positionKey": position_key,
        "weakAnswerSignals": deepcopy(DEFAULT_WEAK_SIGNALS),
        "extraWeakSignals": {},
        "roleMismatchSignals": DEFAULT_WEAK_SIGNALS["irrelevant_answer"],
    }
    if "intern" in position_key or "assistant" in position_key:
        profile["projectQuestionTemplate"] = f"请介绍一次与{label}相关的课程练习或医案分析，重点说明你的判断依据、完成过程和复盘结果。"
    return profile


def _build_profiles() -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    for template_key, group in POSITION_GROUPS.items():
        for position_key, label in group["positions"].items():
            profiles[position_key] = _build_profile(
                template_key,
                position_key,
                label,
                group["category"],
                group["categoryKey"],
            )
    return profiles


INTERVIEW_PROFILES = _build_profiles()


def get_interview_profile(position_key: str | None = None, position_label: str | None = None) -> Dict[str, Any]:
    key = str(position_key or "").strip()
    if key in INTERVIEW_PROFILES:
        return deepcopy(INTERVIEW_PROFILES[key])

    label = str(position_label or "").strip()
    if label:
        for profile in INTERVIEW_PROFILES.values():
            if profile.get("label") == label:
                return deepcopy(profile)

    return deepcopy(INTERVIEW_PROFILES[DEFAULT_POSITION_KEY])


def profile_to_prompt(profile: Dict[str, Any]) -> str:
    core_skills = "、".join(profile.get("coreSkills") or [])
    basic_questions = "\n".join(f"- {item}" for item in profile.get("basicQuestions") or [])
    strong_signals = "、".join((profile.get("strongAnswerSignals") or [])[:80])
    scoring_hints = "\n".join(f"- {item}" for item in profile.get("scoringHints") or [])
    return (
        f"学习方向：{profile.get('label', '')}\n"
        f"课程领域：{profile.get('category', '')}\n"
        f"核心学习能力：{core_skills}\n"
        f"方向强相关信号：{strong_signals}\n"
        f"基础补救题：\n{basic_questions}\n"
        f"评分提示：\n{scoring_hints}"
    )


def _contains_any(content: str, keywords: List[str]) -> bool:
    return any(str(keyword).lower() in content for keyword in keywords)


def detect_profile_skills(text: str, profile: Dict[str, Any]) -> List[str]:
    content = str(text or "").lower()
    covered: List[str] = []
    skill_signals = profile.get("skillSignals") or {}
    for skill in profile.get("coreSkills") or []:
        keywords = skill_signals.get(skill) or [skill.replace("_", " ")]
        if _contains_any(content, keywords):
            covered.append(skill)
    return covered


def public_interview_profiles() -> Dict[str, Dict[str, Any]]:
    return {
        key: {
            "label": profile.get("label"),
            "category": profile.get("category"),
            "categoryKey": profile.get("categoryKey"),
            "coreSkills": profile.get("coreSkills", []),
            "basicQuestions": profile.get("basicQuestions", []),
            "projectQuestionTemplate": profile.get("projectQuestionTemplate", ""),
            "scoringHints": profile.get("scoringHints", []),
        }
        for key, profile in INTERVIEW_PROFILES.items()
    }
