export type NodeLevel = 'root' | 'main' | 'subtopic' | 'knowledge_point';

export interface GraphNode {
  id: string;
  title: string;
  level: NodeLevel;
  domain: string;
  color: string;
  x: number;
  y: number;
  z: number;
  parent?: string;
  summary?: string;
  explanation?: string;
  keywords?: string[];
  tags?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}

const DOMAINS = [
  { name: "基础理论", color: "#ef4444", topics: ["阴阳学说", "五行学说", "精气学说", "整体观念", "辨证论治", "天人相应", "形神一体", "正邪观念", "恒动观念", "体质学说"] },
  { name: "藏象与生命物质", color: "#22c55e", topics: ["心系统", "肝系统", "脾系统", "肺系统", "肾系统", "胆系统", "胃系统", "小肠系统", "大肠系统", "膀胱与三焦"] },
  { name: "经络与腧穴", color: "#06b6d4", topics: ["经络总论", "十二经脉", "奇经八脉", "十五络脉", "十二经别", "十二经筋", "十二皮部", "腧穴总论", "特定穴", "经络辨证"] },
  { name: "四诊与辨证", color: "#eab308", topics: ["望诊", "闻诊", "问诊", "切诊", "八纲辨证", "气血津液辨证", "脏腑辨证", "六经辨证", "卫气营血辨证", "三焦辨证"] },
  { name: "病因病机", color: "#f97316", topics: ["六淫", "疠气", "七情内伤", "饮食失宜", "劳逸失度", "痰饮", "瘀血", "结石与积聚", "病机总论", "疾病传变"] },
  { name: "中药学", color: "#8b5cf6", topics: ["中药性能", "中药炮制", "中药配伍", "用药禁忌", "解表药", "清热药", "祛湿药", "温里理气药", "活血化痰药", "补虚收涩药"] },
  { name: "方剂学", color: "#ec4899", topics: ["方剂组成原则", "方剂剂型与用法", "解表剂", "清热剂", "和解剂", "泻下剂", "温里剂", "补益剂", "理气活血剂", "祛湿祛痰剂"] },
  { name: "常见证候与病证", color: "#f43f5e", topics: ["外感表证", "寒证", "热证", "虚证", "实证", "气病证候", "血病证候", "津液病证候", "痰湿病证候", "脏腑常见证候"] },
  { name: "经典与学术", color: "#84cc16", topics: ["黄帝内经", "难经", "神农本草经", "伤寒论", "金匮要略", "温病条辨", "本草纲目", "景岳全书", "脾胃论", "温热学派"] },
  { name: "治则养生与综合", color: "#14b8a6", topics: ["治则治法", "治未病", "因时制宜", "因地制宜", "因人制宜", "饮食养生", "情志养生", "运动导引", "外治法", "中药质量与安全"] }
];

const SUBTOPIC_TEMPLATES = [
  { name: "概念基础", points: ["定义与边界", "核心术语"] },
  { name: "结构关系", points: ["主要关系", "层次结构"] },
  { name: "动态机制", points: ["变化规律", "平衡机制"] },
  { name: "临床解释", points: ["生理解释", "病理解释"] },
  { name: "关联理论", points: ["相邻概念", "常见辨析"] }
];

function getRandomOffset(baseRadius: number, radiusVariance: number) {
  const r = baseRadius + (Math.random() - 0.5) * 2 * radiusVariance;
  const theta = Math.random() * 2 * Math.PI;
  const phi = Math.acos(2 * Math.random() - 1);
  return {
    x: r * Math.sin(phi) * Math.cos(theta),
    y: r * Math.sin(phi) * Math.sin(theta),
    z: r * Math.cos(phi)
  };
}

function getJitteredFibonacciSpherePoints(samples: number, baseRadius: number, radiusVariance: number) {
  const points = [];
  const phi = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < samples; i++) {
    const y = 1 - (i / (samples - 1)) * 2;
    const rBase = Math.sqrt(1 - y * y);
    const theta = phi * i;
    const r = baseRadius + (Math.random() - 0.5) * 2 * radiusVariance;
    points.push({
      x: Math.cos(theta) * rBase * r,
      y: y * r,
      z: Math.sin(theta) * rBase * r
    });
  }
  return points;
}

function generateGraph() {
  const n: GraphNode[] = [];
  const e: GraphEdge[] = [];

  // Root
  n.push({
    id: "TCM_ROOT",
    title: "中医药知识库",
    level: "root",
    domain: "总览",
    color: "#ffffff",
    x: 0, y: 0, z: 0,
    summary: "用于前端知识图谱原型，总节点1601个。",
    explanation: "本知识库以中医基础理论、藏象经络、四诊辨证、病因病机、中药方剂、经典学术及养生治则等内容构成多层级知识网络，主要用于可视化浏览、学习导航和知识关联展示。内容为原型展示资料，不替代专业医疗判断。"
  });

  const mainPoints = getJitteredFibonacciSpherePoints(100, 18, 6);
  let mainIdx = 0;

  DOMAINS.forEach((domain, dIdx) => {
    domain.topics.forEach((topicName, tIdx) => {
      const mainId = `M${(mainIdx + 1).toString().padStart(3, '0')}`;
      const mPos = mainPoints[mainIdx];
      
      n.push({
        id: mainId,
        title: topicName,
        level: "main",
        domain: domain.name,
        color: domain.color,
        parent: "TCM_ROOT",
        x: mPos.x, y: mPos.y, z: mPos.z,
        summary: `${topicName}是【${domain.name}】领域中的主要知识节点。`,
        explanation: `“${topicName}”是“${domain.name}”领域中的核心主题之一，主要用于组织这一方向的基本概念、关系、变化规律及其相关知识。从知识结构上看，“${topicName}”承担的是总览作用，适合先建立概念边界，再继续查看下层的具体机制、表现和关联知识。理解时应关注概念之间的相互关系，避免把具有动态含义的理论机械地理解成固定对应。`,
        keywords: [`${topicName}·基本规律`, `${topicName}·核心理论`, `${topicName}·临床应用`]
      });
      e.push({ source: "TCM_ROOT", target: mainId });

      // Subtopics (5 per main)
      SUBTOPIC_TEMPLATES.forEach((subTpl, sIdx) => {
        const subId = `${mainId}_C${sIdx + 1}`;
        const sPos = getRandomOffset(4, 2);
        n.push({
          id: subId,
          title: `${topicName}·${subTpl.name}`,
          level: "subtopic",
          domain: domain.name,
          color: domain.color,
          parent: mainId,
          x: mPos.x + sPos.x, y: mPos.y + sPos.y, z: mPos.z + sPos.z,
          summary: `围绕“${topicName}”的${subTpl.name}展开。`,
          explanation: `在“${topicName}”这一主题中，“${subTpl.name}”用于把较大的知识范围进一步拆开，帮助区分不同机制、表现或应用场景。它并不是独立于主主题的另一套理论，而是从一个特定角度对“${topicName}”进行细化。`
        });
        e.push({ source: mainId, target: subId });

        // Knowledge Points (2 per subtopic)
        subTpl.points.forEach((kpName, kIdx) => {
          const kpId = `${subId}_G${kIdx + 1}`;
          const kPos = getRandomOffset(2, 1);
          n.push({
            id: kpId,
            title: `${topicName}·${kpName}`,
            level: "knowledge_point",
            domain: domain.name,
            color: domain.color, // Could fade it here if wanted
            parent: subId,
            x: mPos.x + sPos.x + kPos.x, 
            y: mPos.y + sPos.y + kPos.y, 
            z: mPos.z + sPos.z + kPos.z,
            summary: `${topicName}中的具体知识点：${kpName}`,
            explanation: `“${topicName}·${kpName}”是“${subTpl.name}”下的具体知识点，当前条目主要围绕“${kpName}”展开。它用于把上一级概念进一步落实到可识别、可比较的内容上，并与关键词“${topicName}·${kpName}”建立联系。理解时应先放回“${topicName}”的整体框架，再结合相邻节点比较其异同。`,
            tags: [topicName, subTpl.name, kpName]
          });
          e.push({ source: subId, target: kpId });
        });
      });

      mainIdx++;
    });
  });

  return { nodes: n, edges: e };
}

export const { nodes, edges } = generateGraph();
