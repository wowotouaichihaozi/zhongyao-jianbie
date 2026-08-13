import assert from 'node:assert/strict'
import test from 'node:test'

import {
  extractTaskResources,
  findTaskResource,
  resourceContentText,
  resourceCitationCount,
  taskIdFromResourceId,
} from '../src/utils/personalizedResourceHistory.js'
import {
  buildSandboxedHtmlDocument,
  mermaidMindmapSource,
  renderSafeMarkdown,
  safeResourceHref,
} from '../src/utils/resourceMarkdown.js'

const completedTask = {
  taskId: 'xz_demo_1',
  taskType: 'personalized_resources',
  title: 'GPIO 个性化资源',
  status: 'complete',
  createdAt: '2026-08-14T02:00:00Z',
  result: {
    orchestrator: 'xiaozhi-companion-agent',
    orchestration: {
      runId: 'run-demo-1',
      profileReportId: 17,
      review: { passed: true, score: 92 },
      agentRuns: [{ agentId: 'learning-document-agent' }],
    },
    workflow: {
      grounded: true,
      planner: { targetWeakPoints: ['GPIO 输入模式'] },
      resources: [{
        id: 'handout',
        type: 'document',
        title: 'GPIO 讲义',
        matchScore: 94,
        content: '# GPIO',
        metadata: {
          workflowNode: 'learning_document_agent',
          qualityEvaluation: { score: 88, passed: true, citationCount: 1, reviewStatus: 'passed' },
          knowledgeSources: [{ id: 'KB-1', title: 'GPIO 课程资料' }],
        },
      }],
    },
  },
}

test('normalizes task resources with real audit and profile metadata', () => {
  const [resource] = extractTaskResources(completedTask)
  assert.equal(resource.id, 'task:xz_demo_1:handout')
  assert.equal(resource.metadata.runId, 'run-demo-1')
  assert.equal(resource.metadata.profileReportId, 17)
  assert.deepEqual(resource.metadata.planner.targetWeakPoints, ['GPIO 输入模式'])
  assert.equal(resource.qualityEvaluation.score, 88)
  assert.equal(resourceCitationCount(resource), 1)
})

test('restores an exact task-backed resource and exposes its task id', () => {
  const resourceId = 'task:xz_demo_1:handout'
  assert.equal(taskIdFromResourceId(resourceId), 'xz_demo_1')
  assert.equal(findTaskResource(completedTask, resourceId)?.title, 'GPIO 讲义')
  assert.equal(findTaskResource(completedTask, 'task:xz_demo_1:missing'), null)
})

test('renders supported markdown while escaping executable markup and unsafe links', () => {
  const html = renderSafeMarkdown('# 标题\n\n<script>alert(1)</script>\n\n[危险](javascript:alert(1))\n\n[来源](https://example.com/a?q=1&x=2)')
  assert.match(html, /<h1>标题<\/h1>/)
  assert.doesNotMatch(html, /<script>/)
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/)
  assert.doesNotMatch(html, /javascript:/)
  assert.match(html, /href="https:\/\/example\.com\/a\?q=1&amp;x=2"/)
})

test('normalizes structured content and isolates HTML PPT documents', () => {
  assert.equal(resourceContentText({ content: { document: { markdown: '# 讲义' } } }), '# 讲义')
  assert.match(resourceContentText({ content: { questions: [{ title: 'GPIO' }] } }), /^```json/)
  assert.equal(safeResourceHref('javascript:alert(1)'), '')
  assert.equal(safeResourceHref('/api/resource/1'), '/api/resource/1')

  const document = buildSandboxedHtmlDocument('<article><script>alert(1)</script></article>')
  assert.match(document, /Content-Security-Policy/)
  assert.match(document, /default-src 'none'/)
  assert.match(document, /img-src data: blob:/)
  assert.match(document, /media-src data: blob:/)
  assert.doesNotMatch(document, /img-src https:/)
  assert.doesNotMatch(document, /media-src https:/)
  assert.match(document, /<article><script>alert\(1\)<\/script><\/article>/)
})

test('uses Mermaid only for explicit mindmap syntax and keeps heading maps as Markdown', () => {
  assert.equal(mermaidMindmapSource('# GPIO\n\n## 输入模式'), '')
  assert.equal(
    mermaidMindmapSource('```mermaid\nmindmap\n  root((GPIO))\n```'),
    'mindmap\n  root((GPIO))',
  )
  assert.equal(mermaidMindmapSource('mindmap\n  root((GPIO))'), 'mindmap\n  root((GPIO))')
})
