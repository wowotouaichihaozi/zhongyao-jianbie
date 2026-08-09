export function buildElementPickerCoreScript(): string {
  return `
  const createPptElementPicker = (options) => {
    const doc = options.document || document;
    let active = false;
    let moveHandler = null;
    let clickHandler = null;
    let keyHandler = null;

    const isPointInRect = (rect, clientX, clientY) => {
      return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
    };

    const getCaretElementAtPoint = (clientX, clientY) => {
      if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
      let node = null;
      try {
        if (typeof doc.caretPositionFromPoint === "function") {
          node = doc.caretPositionFromPoint(clientX, clientY)?.offsetNode || null;
        } else if (typeof doc.caretRangeFromPoint === "function") {
          node = doc.caretRangeFromPoint(clientX, clientY)?.startContainer || null;
        }
      } catch (_error) {}
      if (!node) return null;
      if (node instanceof Element) return node;
      if (node.nodeType === Node.TEXT_NODE && node.parentElement instanceof Element) {
        return node.parentElement;
      }
      return node.parentElement instanceof Element ? node.parentElement : null;
    };

    const getInspectorPointElements = (root, clientX, clientY, fallbackElement) => {
      const normalStack = typeof doc.elementsFromPoint === "function"
        ? doc.elementsFromPoint(clientX, clientY)
        : [];
      let inspectorStack = [];
      let style = null;
      try {
        style = doc.createElement("style");
        style.textContent = '.ppt-page-root *, [data-ppt-guard-root="1"] * { pointer-events: auto !important; }';
        doc.head.appendChild(style);
        inspectorStack = typeof doc.elementsFromPoint === "function"
          ? doc.elementsFromPoint(clientX, clientY)
          : [];
      } catch (_error) {
        inspectorStack = [];
      } finally {
        if (style) style.remove();
      }

      const merged = [];
      const seen = new Set();
      [inspectorStack, normalStack, [fallbackElement]].forEach((stack) => {
        stack.forEach((element) => {
          if (!(element instanceof Element)) return;
          if (!root.contains(element)) return;
          if (seen.has(element)) return;
          seen.add(element);
          merged.push(element);
        });
      });
      return merged;
    };

    const pickFromCandidateChain = (root, element, clientX, clientY, seen) => {
      let current = element;
      while (current && current instanceof Element && root.contains(current)) {
        if (seen.has(current)) {
          current = current.parentElement;
          continue;
        }
        seen.add(current);
        if (options.isSelectable(current)) {
          const selector = options.getSelector(current);
          const rect = current.getBoundingClientRect();
          if (selector && isPointInRect(rect, clientX, clientY)) return current;
        }
        if (current === root) break;
        current = current.parentElement;
      }
      return null;
    };

    const pickTextTarget = (root, clientX, clientY, seen) => {
      const textElement = getCaretElementAtPoint(clientX, clientY);
      if (!textElement || !root.contains(textElement)) return null;
      const boundaryRoot = options.getContentRoot(textElement) || options.getPageRoot(textElement) || root;
      let candidate = textElement;
      while (candidate && candidate !== boundaryRoot) {
        const target = pickFromCandidateChain(root, candidate, clientX, clientY, seen);
        if (target) return target;
        candidate = candidate.parentElement;
      }
      return null;
    };

    const pickAtPointBase = (origin, clientX, clientY) => {
      if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
      const hitElement = doc.elementFromPoint(clientX, clientY);
      const root =
        options.getPageRoot(origin) ||
        options.getPageRoot(hitElement) ||
        doc.querySelector(".ppt-page-root, [data-ppt-guard-root='1']");
      if (!root) return null;

      const seen = new Set();
      const textCandidate = pickTextTarget(root, clientX, clientY, seen);
      if (textCandidate) return textCandidate;

      const pointElements = getInspectorPointElements(root, clientX, clientY, hitElement);
      for (const element of pointElements) {
        const candidate = pickFromCandidateChain(root, element, clientX, clientY, seen);
        if (candidate) return candidate;
      }
      return null;
    };

    const pickAtPoint = (origin, clientX, clientY) => {
      const target = pickAtPointBase(origin, clientX, clientY);
      if (typeof options.resolveTarget === "function") {
        const resolved = options.resolveTarget({
          origin,
          clientX,
          clientY,
          target,
          pickAtPointBase,
        });
        if (resolved !== undefined) return resolved;
      }
      return target;
    };

    const start = (handlers) => {
      if (active) return;
      active = true;
      moveHandler = (event) => {
        const target = pickAtPoint(event.target, event.clientX, event.clientY);
        handlers.onHover?.(target, event);
      };
      clickHandler = (event) => {
        const target = pickAtPoint(event.target, event.clientX, event.clientY);
        if (!target) return;
        const handled = handlers.onClick?.(target, event);
        if (handled !== false) {
          event.preventDefault();
          event.stopPropagation();
        }
      };
      keyHandler = (event) => {
        const handled = handlers.onKeyDown?.(event);
        if (handled) {
          event.preventDefault();
          event.stopPropagation();
        }
      };
      doc.addEventListener("mousemove", moveHandler, true);
      doc.addEventListener("click", clickHandler, true);
      doc.addEventListener("keydown", keyHandler, true);
    };

    const stop = () => {
      if (!active) return;
      active = false;
      if (moveHandler) doc.removeEventListener("mousemove", moveHandler, true);
      if (clickHandler) doc.removeEventListener("click", clickHandler, true);
      if (keyHandler) doc.removeEventListener("keydown", keyHandler, true);
      moveHandler = null;
      clickHandler = null;
      keyHandler = null;
    };

    return { pickAtPoint, start, stop };
  };
  `;
}
