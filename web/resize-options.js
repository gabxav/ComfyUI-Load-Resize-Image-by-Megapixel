import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "LoadResizeMP.LegacyWidgets",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LoadImageResizeMP") return;

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            const result = onConfigure?.apply(this, arguments);
            const index = this.widgets?.findIndex((widget) => widget.name === "only_downscale");
            if (index >= 0 && typeof data.widgets_values?.[index] !== "boolean") {
                // Old workflows stored the upload button's "image" value at this index.
                this.widgets[index].value = false;
            }
            return result;
        };
    },
});
