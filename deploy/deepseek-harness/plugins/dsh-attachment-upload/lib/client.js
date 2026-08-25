window.__ModuleLoader__.load({ id: 'lzhan-dsh-attachment-upload', factory: (require) => {
  const module = { exports: {} }
  const exports = module.exports
  const React = require('react')

  const MAX_BYTES = 64 * 1024 * 1024
  const buttonStyle = {
    alignItems: 'center', background: 'transparent', border: '0', borderRadius: 6,
    color: 'inherit', cursor: 'pointer', display: 'inline-flex', gap: 5,
    height: 32, padding: '0 8px', fontSize: 12,
  }
  const errorStyle = { color: '#c2413b', fontSize: 11, maxWidth: 420, whiteSpace: 'pre-wrap' }

  function PaperclipIcon() {
    return React.createElement('svg', {
      width: 17, height: 17, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
      strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': 'true',
    }, React.createElement('path', { d: 'm21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48' }))
  }

  function AttachmentButton(props) {
    const [busy, setBusy] = React.useState(false)
    const [error, setError] = React.useState('')
    const fileRef = React.useRef(null)
    const draftRef = React.useRef('')
    const inputState = props.useInput ? props.useInput((state) => state) : null
    if (inputState && typeof inputState.draft === 'string') draftRef.current = inputState.draft

    const upload = async (files) => {
      setBusy(true)
      setError('')
      try {
        const lines = []
        for (const file of files) {
          if (file.size > MAX_BYTES) throw new Error(`${file.name} 超过 64 MB 限制`)
          const response = await fetch('/_dsh/attachment-upload/upload', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/octet-stream',
              'x-file-name': encodeURIComponent(file.name),
            },
            body: await file.arrayBuffer(),
          })
          const result = await response.json()
          if (!response.ok || !result?.ok) throw new Error(result?.reason || `${file.name} 上传失败`)
          lines.push(`附件文件: ${result.path}`)
          if (result.extracted?.path) lines.push(`ZIP 已安全解压: ${result.extracted.path}`)
        }
        if (!props.inputActions || typeof props.inputActions.setDraft !== 'function') {
          throw new Error('输入框暂时不可用')
        }
        const addition = lines.join('\n')
        props.inputActions.setDraft(draftRef.current ? `${draftRef.current}\n${addition}` : addition)
      } catch (uploadError) {
        setError(String(uploadError?.message || uploadError))
      } finally {
        setBusy(false)
        if (fileRef.current) fileRef.current.value = ''
      }
    }

    return React.createElement(React.Fragment, null,
      React.createElement('input', {
        ref: fileRef, type: 'file', multiple: true, style: { display: 'none' },
        onChange: (event) => {
          const files = Array.from(event.target?.files || [])
          if (files.length) void upload(files)
        },
      }),
      React.createElement('button', {
        type: 'button', disabled: busy, style: { ...buttonStyle, opacity: busy ? 0.55 : 1 },
        title: '上传文件到共享工作区；ZIP 会经过安全检查后解压',
        'aria-label': busy ? '正在上传附件' : '上传附件',
        onClick: () => fileRef.current?.click(),
      }, React.createElement(PaperclipIcon), React.createElement('span', null, busy ? '上传中' : '附件')),
      error ? React.createElement('div', { role: 'alert', style: errorStyle }, error) : null,
    )
  }

  function apply(ctx) {
    const slots = ctx.get('slots')
    if (!slots) return
    slots.inject('conversation.input.left', () => slots.register(
      { name: 'conversation.input.left', id: 'lzhan-attachment-upload', order: 5, label: '附件' },
      AttachmentButton,
    ))
  }

  exports.apply = apply
  return module.exports
} })
