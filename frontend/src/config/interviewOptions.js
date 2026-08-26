export const DIFFICULTY_OPTIONS = [
  { value: 'intern', label: '启蒙' },
  { value: 'campus', label: '入门' },
  { value: 'basic', label: '基础' },
  { value: 'medium', label: '进阶' },
  { value: 'advanced', label: '综合' },
]

/* Legacy option values are intentionally preserved below so old saved sessions
 * remain readable; only INTERVIEW_CATEGORIES is exported to the active UI. */
const mcuDirections = [
  { label: 'GPIO / 按键 / LED', value: 'gpio_key_led' },
  { label: 'GPIO / 中断 / UART', value: 'gpio_interrupt_uart' },
  { label: '定时器 / PWM / ADC', value: 'timer_pwm_adc' },
  { label: '串口通信 / 数据收发', value: 'uart_data_transfer' },
  { label: '数码管 / 蜂鸣器 / 外设控制', value: 'display_buzzer_peripheral' },
  { label: '传感器采集实验', value: 'sensor_collection_experiment' },
  { label: '单片机项目经验综合', value: 'mcu_project' },
  { label: '实验接线与调试', value: 'wiring_debugging' },
]

const embeddedDirections = [
  { label: 'C 语言 / 指针 / 位操作', value: 'c_pointer_bit' },
  { label: 'STM32 / GPIO / 中断 / UART', value: 'stm32_gpio_interrupt_uart' },
  { label: '外设控制逻辑', value: 'peripheral_control_logic' },
  { label: '数据采集与处理', value: 'data_collection_processing' },
  { label: '低功耗设计基础', value: 'low_power_basics' },
  { label: '通信协议应用', value: 'communication_protocols' },
  { label: '中医项目经验综合', value: 'embedded_project' },
  { label: '问题排查与调试', value: 'debugging_troubleshooting' },
]

const linuxDriverDirections = [
  { label: 'Linux 基础命令', value: 'linux_basic_commands' },
  { label: '交叉编译基础', value: 'cross_compilation' },
  { label: '字符设备驱动入门', value: 'char_device_driver' },
  { label: 'GPIO / I2C / SPI / UART 驱动', value: 'gpio_i2c_spi_uart_driver' },
  { label: '设备树基础', value: 'device_tree_basics' },
  { label: 'BSP 适配基础', value: 'bsp_porting_basics' },
  { label: '驱动调试与日志分析', value: 'driver_debugging_logs' },
]

const rtosDirections = [
  { label: 'FreeRTOS 基础', value: 'freertos_basics' },
  { label: '任务 / 队列 / 信号量', value: 'task_queue_semaphore' },
  { label: '任务优先级与调度', value: 'priority_scheduling' },
  { label: '定时器与中断协同', value: 'timer_interrupt_coordination' },
  { label: '多任务通信', value: 'multitask_communication' },
  { label: '实时系统项目经验', value: 'rtos_project' },
  { label: 'RTOS 问题排查', value: 'rtos_debugging' },
]

const iotDirections = [
  { label: '传感器数据采集', value: 'sensor_data_collection' },
  { label: 'MQTT / HTTP / TCP 基础', value: 'mqtt_http_tcp' },
  { label: 'WiFi / 蓝牙 / 串口通信', value: 'wifi_bluetooth_uart' },
  { label: '设备上云', value: 'device_cloud' },
  { label: '远程控制', value: 'remote_control' },
  { label: '数据上传与解析', value: 'data_upload_parse' },
  { label: '智能硬件项目经验', value: 'smart_hardware_project' },
  { label: '物联网通信故障排查', value: 'iot_comm_debugging' },
]

const hardwareDirections = [
  { label: '模拟电路基础', value: 'analog_circuit_basics' },
  { label: '数字电路基础', value: 'digital_circuit_basics' },
  { label: '常用电子元器件', value: 'electronic_components' },
  { label: '原理图阅读', value: 'schematic_reading' },
  { label: 'PCB 基础', value: 'pcb_basics' },
  { label: '电源电路', value: 'power_circuit' },
  { label: '万用表 / 示波器使用', value: 'multimeter_oscilloscope' },
  { label: '硬件故障排查', value: 'hardware_fault_debugging' },
]

const testSupportDirections = [
  { label: '功能测试', value: 'functional_testing' },
  { label: '串口调试', value: 'uart_debugging' },
  { label: '接口测试', value: 'interface_testing' },
  { label: 'Bug 复现与记录', value: 'bug_reproduction_record' },
  { label: '板卡测试', value: 'board_testing' },
  { label: '烧录与下载问题排查', value: 'flashing_download_debugging' },
  { label: '测试报告', value: 'test_report' },
  { label: '客户问题定位', value: 'customer_issue_diagnosis' },
]

const automationDirections = [
  { label: '输入输出控制', value: 'io_control' },
  { label: '继电器 / 电机控制', value: 'relay_motor_control' },
  { label: 'PLC / MCU 基础', value: 'plc_mcu_basics' },
  { label: '传感器采集', value: 'sensor_collection' },
  { label: '控制流程设计', value: 'control_flow_design' },
  { label: '工业通信基础', value: 'industrial_communication' },
  { label: '机器人运动控制入门', value: 'robot_motion_basics' },
  { label: '自动化项目经验', value: 'automation_project' },
]

const LEGACY_INTERVIEW_CATEGORIES = [
  {
    label: '单片机与 MCU 开发',
    value: 'mcu_development',
    positions: [
      { label: '单片机开发工程师', value: 'mcu_developer', directions: mcuDirections },
      { label: 'STM32 开发工程师', value: 'stm32_developer', directions: mcuDirections },
      { label: '51 单片机开发工程师', value: 'mcs51_developer', directions: mcuDirections },
      { label: 'MCU 实验开发工程师', value: 'mcu_experiment_developer', directions: mcuDirections },
      { label: '单片机课程助教 / 实验助理', value: 'mcu_lab_assistant', directions: mcuDirections },
      { label: '单片机实习生', value: 'mcu_intern', directions: mcuDirections },
    ],
  },
  {
    label: '中医软件开发',
    value: 'embedded_software',
    positions: [
      { label: '中医软件工程师', value: 'embedded_software_engineer', directions: embeddedDirections },
      { label: '中医应用工程师', value: 'embedded_application_engineer', directions: embeddedDirections },
      { label: '中医 C 开发工程师', value: 'embedded_c_engineer', directions: embeddedDirections },
      { label: '中医项目开发工程师', value: 'embedded_project_engineer', directions: embeddedDirections },
      { label: '中医助理工程师', value: 'embedded_assistant_engineer', directions: embeddedDirections },
      { label: '中医实习生', value: 'embedded_intern', directions: embeddedDirections },
    ],
  },
  {
    label: '中医 Linux / 驱动开发',
    value: 'embedded_linux_driver',
    positions: [
      { label: '中医 Linux 工程师', value: 'embedded_linux_engineer', directions: linuxDriverDirections },
      { label: 'Linux 驱动工程师', value: 'linux_driver_engineer', directions: linuxDriverDirections },
      { label: 'BSP 工程师', value: 'bsp_engineer', directions: linuxDriverDirections },
      { label: '外设驱动工程师', value: 'peripheral_driver_engineer', directions: linuxDriverDirections },
      { label: '板级支持工程师', value: 'board_support_engineer', directions: linuxDriverDirections },
    ],
  },
  {
    label: 'RTOS 与实时系统',
    value: 'rtos_realtime',
    positions: [
      { label: 'RTOS 开发工程师', value: 'rtos_developer', directions: rtosDirections },
      { label: 'FreeRTOS 应用工程师', value: 'freertos_application_engineer', directions: rtosDirections },
      { label: '实时任务调度开发工程师', value: 'realtime_scheduler_engineer', directions: rtosDirections },
      { label: '中医系统工程师', value: 'embedded_system_engineer', directions: rtosDirections },
    ],
  },
  {
    label: '物联网与智能硬件',
    value: 'iot_smart_hardware',
    positions: [
      { label: '物联网中医工程师', value: 'iot_embedded_engineer', directions: iotDirections },
      { label: 'IoT 应用开发工程师', value: 'iot_application_engineer', directions: iotDirections },
      { label: '智能硬件开发工程师', value: 'smart_hardware_engineer', directions: iotDirections },
      { label: '工业物联网工程师', value: 'industrial_iot_engineer', directions: iotDirections },
      { label: '设备联网工程师', value: 'device_networking_engineer', directions: iotDirections },
    ],
  },
  {
    label: '硬件与电子设计',
    value: 'hardware_electronics',
    positions: [
      { label: '硬件工程师', value: 'hardware_engineer', directions: hardwareDirections },
      { label: '电子工程师', value: 'electronics_engineer', directions: hardwareDirections },
      { label: 'PCB 助理工程师', value: 'pcb_assistant_engineer', directions: hardwareDirections },
      { label: '电路调试工程师', value: 'circuit_debug_engineer', directions: hardwareDirections },
      { label: '硬件助理工程师', value: 'hardware_assistant_engineer', directions: hardwareDirections },
      { label: '电子工程实习生', value: 'electronics_intern', directions: hardwareDirections },
    ],
  },
  {
    label: '测试、调试与技术支持',
    value: 'testing_debug_support',
    positions: [
      { label: '中医测试工程师', value: 'embedded_test_engineer', directions: testSupportDirections },
      { label: '硬件测试工程师', value: 'hardware_test_engineer', directions: testSupportDirections },
      { label: '单片机调试工程师', value: 'mcu_debug_engineer', directions: testSupportDirections },
      { label: '技术支持工程师', value: 'technical_support_engineer', directions: testSupportDirections },
      { label: '实验设备维护工程师', value: 'lab_equipment_maintenance_engineer', directions: testSupportDirections },
      { label: '板卡测试工程师', value: 'board_test_engineer', directions: testSupportDirections },
    ],
  },
  {
    label: '自动化与工业控制',
    value: 'automation_industrial_control',
    positions: [
      { label: '自动化控制工程师', value: 'automation_control_engineer', directions: automationDirections },
      { label: '电气控制工程师', value: 'electrical_control_engineer', directions: automationDirections },
      { label: '机器人控制工程师', value: 'robot_control_engineer', directions: automationDirections },
      { label: '工业控制入门工程师', value: 'industrial_control_entry_engineer', directions: automationDirections },
      { label: '传感器应用工程师', value: 'sensor_application_engineer', directions: automationDirections },
    ],
  },
]

const tcmFoundationDirections = [
  { label: '阴阳五行', value: 'yin_yang_five_phases' },
  { label: '藏象学说', value: 'zang_xiang' },
  { label: '气血津液', value: 'qi_blood_fluids' },
  { label: '经络学说', value: 'meridian_theory' },
  { label: '病因病机', value: 'etiology_pathogenesis' },
  { label: '体质辨识', value: 'constitution_identification' },
]

const tcmDiagnosisDirections = [
  { label: '望诊与舌诊', value: 'inspection_tongue' },
  { label: '闻诊与问诊', value: 'listening_inquiry' },
  { label: '切诊与脉诊', value: 'palpation_pulse' },
  { label: '八纲辨证', value: 'eight_principles' },
  { label: '脏腑辨证', value: 'zang_fu_differentiation' },
  { label: '四诊合参', value: 'four_diagnostics' },
]

const materiaMedicaDirections = [
  { label: '中药性味归经', value: 'properties_meridians' },
  { label: '中药功效主治', value: 'effects_indications' },
  { label: '中药炮制与鉴别', value: 'processing_identification' },
  { label: '方剂组成与功效', value: 'formula_composition' },
  { label: '君臣佐使', value: 'formula_roles' },
  { label: '配伍禁忌与安全用药', value: 'compatibility_safety' },
]

const clinicalDirections = [
  { label: '感冒咳嗽医案', value: 'cold_cough_cases' },
  { label: '脾胃病医案', value: 'spleen_stomach_cases' },
  { label: '心系病证医案', value: 'heart_system_cases' },
  { label: '肝胆病证医案', value: 'liver_gallbladder_cases' },
  { label: '肾系病证医案', value: 'kidney_system_cases' },
  { label: '综合医案辨析', value: 'integrated_case_analysis' },
]

const classicsDirections = [
  { label: '《黄帝内经》选读', value: 'huangdi_neijing' },
  { label: '《伤寒论》六经辨证', value: 'shanghan_six_channels' },
  { label: '《金匮要略》选读', value: 'jingui_yaolue' },
  { label: '经典条文理解', value: 'classics_comprehension' },
  { label: '经方医案', value: 'classical_formula_cases' },
]

const acupunctureDirections = [
  { label: '经络腧穴基础', value: 'meridian_acupoints' },
  { label: '常用腧穴定位', value: 'acupoint_location' },
  { label: '配穴原则', value: 'acupoint_compatibility' },
  { label: '针灸治疗原则', value: 'acupuncture_principles' },
  { label: '推拿基础手法', value: 'tuina_techniques' },
]

const wellnessDirections = [
  { label: '中医体质养生', value: 'constitution_wellness' },
  { label: '四时养生', value: 'seasonal_wellness' },
  { label: '饮食调养', value: 'dietary_regulation' },
  { label: '情志调摄', value: 'emotion_regulation' },
  { label: '运动导引', value: 'exercise_daoyin' },
]

const researchDirections = [
  { label: '中医文献检索', value: 'tcm_literature' },
  { label: '医案数据整理', value: 'case_data' },
  { label: '中医知识图谱', value: 'tcm_knowledge_graph' },
  { label: '中医药循证评价', value: 'tcm_evidence' },
  { label: '中医药健康管理', value: 'tcm_health_management' },
]

export const INTERVIEW_CATEGORIES = [
  {
    label: '中医基础理论',
    value: 'mcu_development',
    positions: [
      { label: '中医基础理论学习者', value: 'mcu_developer', directions: tcmFoundationDirections },
      { label: '藏象与气血津液专项', value: 'stm32_developer', directions: tcmFoundationDirections },
      { label: '病因病机专项', value: 'mcs51_developer', directions: tcmFoundationDirections },
      { label: '中医体质辨识专项', value: 'mcu_experiment_developer', directions: tcmFoundationDirections },
    ],
  },
  {
    label: '中医诊断学',
    value: 'embedded_software',
    positions: [
      { label: '四诊基础学习者', value: 'embedded_software_engineer', directions: tcmDiagnosisDirections },
      { label: '八纲辨证专项', value: 'embedded_application_engineer', directions: tcmDiagnosisDirections },
      { label: '脏腑辨证专项', value: 'embedded_c_engineer', directions: tcmDiagnosisDirections },
      { label: '舌脉辨析专项', value: 'embedded_project_engineer', directions: tcmDiagnosisDirections },
    ],
  },
  {
    label: '中药学与方剂学',
    value: 'embedded_linux_driver',
    positions: [
      { label: '中药学学习者', value: 'embedded_linux_engineer', directions: materiaMedicaDirections },
      { label: '方剂学学习者', value: 'linux_driver_engineer', directions: materiaMedicaDirections },
      { label: '方药配伍专项', value: 'bsp_engineer', directions: materiaMedicaDirections },
      { label: '安全用药专项', value: 'peripheral_driver_engineer', directions: materiaMedicaDirections },
    ],
  },
  {
    label: '中医经典',
    value: 'rtos_realtime',
    positions: [
      { label: '《黄帝内经》学习者', value: 'rtos_developer', directions: classicsDirections },
      { label: '《伤寒论》学习者', value: 'freertos_application_engineer', directions: classicsDirections },
      { label: '《金匮要略》学习者', value: 'realtime_scheduler_engineer', directions: classicsDirections },
    ],
  },
  {
    label: '中医临床医案',
    value: 'iot_smart_hardware',
    positions: [
      { label: '中医内科医案学习者', value: 'iot_embedded_engineer', directions: clinicalDirections },
      { label: '中医妇科医案学习者', value: 'iot_application_engineer', directions: clinicalDirections },
      { label: '中医儿科医案学习者', value: 'smart_hardware_engineer', directions: clinicalDirections },
      { label: '综合医案辨析学习者', value: 'industrial_iot_engineer', directions: clinicalDirections },
    ],
  },
  {
    label: '针灸推拿',
    value: 'hardware_electronics',
    positions: [
      { label: '针灸基础学习者', value: 'hardware_engineer', directions: acupunctureDirections },
      { label: '经络腧穴专项', value: 'electronics_engineer', directions: acupunctureDirections },
      { label: '配穴与治疗专项', value: 'pcb_assistant_engineer', directions: acupunctureDirections },
      { label: '推拿基础学习者', value: 'circuit_debug_engineer', directions: acupunctureDirections },
    ],
  },
  {
    label: '中医养生与健康管理',
    value: 'testing_debug_support',
    positions: [
      { label: '中医养生学习者', value: 'embedded_test_engineer', directions: wellnessDirections },
      { label: '体质调养专项', value: 'hardware_test_engineer', directions: wellnessDirections },
      { label: '四时养生专项', value: 'mcu_debug_engineer', directions: wellnessDirections },
      { label: '健康管理学习者', value: 'technical_support_engineer', directions: wellnessDirections },
    ],
  },
  {
    label: '中医药研究与数字化',
    value: 'automation_industrial_control',
    positions: [
      { label: '中医文献研究学习者', value: 'automation_control_engineer', directions: researchDirections },
      { label: '医案数据研究学习者', value: 'electrical_control_engineer', directions: researchDirections },
      { label: '中医知识工程学习者', value: 'robot_control_engineer', directions: researchDirections },
      { label: '中医药循证学习者', value: 'industrial_control_entry_engineer', directions: researchDirections },
    ],
  },
]

export function findOption(options, value) {
  return options.find((item) => item.value === value) || options[0]
}
