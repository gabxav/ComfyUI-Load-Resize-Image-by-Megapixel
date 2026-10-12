import { app } from "../../scripts/app.js";

const resizeControls = new Set([
    "megapixels", "divisible_by", "upscale_method", "rounding", "fit_mode", "only_downscale",
]);
const hiddenWidgets = new WeakMap();

function updateResizeControls(node, resizeNode = false) {
    const resize = node.widgets?.find((widget) => widget.name === "resize");
    const resizeInput = node.inputs?.find((input) => input.name === "resize");
    // A connected resize input is controlled upstream, so keep its settings available.
    const enabled = Boolean(resize?.value) || resizeInput?.link != null;
    const previousHeight = node.computeSize()[1];
    let changed = false;

    for (const widget of node.widgets ?? []) {
        if (!resizeControls.has(widget.name)) continue;
        const previous = hiddenWidgets.get(widget);
        if (!enabled && !previous) {
            hiddenWidgets.set(widget, { hidden: widget.hidden, optionsHidden: widget.options?.hidden });
            widget.hidden = true;
            widget.options = { ...widget.options, hidden: true };
            changed = true;
        } else if (enabled && previous) {
            widget.hidden = previous.hidden ?? false;
            widget.options.hidden = previous.optionsHidden ?? false;
            hiddenWidgets.delete(widget);
            changed = true;
        }
    }

    if (changed && resizeNode) {
        const height = node.computeSize()[1];
        node.setSize([node.size[0], Math.max(height, node.size[1] + height - previousHeight)]);
    }
    if (changed) node.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "LoadResizeMP.ResizeOptions",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!["LoadImageResizeMP", "ImageResizeMP"].includes(nodeData.name)) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const resize = this.widgets?.find((widget) => widget.name === "resize");
            if (resize) {
                const callback = resize.callback;
                const node = this;
                resize.callback = function () {
                    const value = callback?.apply(this, arguments);
                    updateResizeControls(node, true);
                    return value;
                };
            }
            updateResizeControls(this);
            return result;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            const result = onConfigure?.apply(this, arguments);
            const index = this.widgets?.findIndex((widget) => widget.name === "only_downscale");
            if (nodeData.name === "LoadImageResizeMP" && index >= 0 && typeof data.widgets_values?.[index] !== "boolean") {
                // Old workflows stored the upload button's "image" value at this index.
                this.widgets[index].value = false;
            }
            // Saved node dimensions already reflect visibility; do not shrink them again.
            updateResizeControls(this);
            return result;
        };

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, slot) {
            const result = onConnectionsChange?.apply(this, arguments);
            if (type === globalThis.LiteGraph.INPUT && this.inputs?.[slot]?.name === "resize") {
                updateResizeControls(this, true);
            }
            return result;
        };
    },
});
