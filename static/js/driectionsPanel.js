const panel = document.getElementById("directionsPanel");
const header = document.getElementById("directionsPanelHeader");
const content = document.getElementById("directionsPanelContent");
const collapseBtn = document.getElementById("collapseDirections");
const closeBtn = document.getElementById("closeDirections");
const resizeHandle = document.getElementById("resizeHandle");

// COLLAPSE toggle
collapseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const icon = collapseBtn.querySelector("i");
  const isCollapsed = content.style.display === "none";
  content.style.display = isCollapsed ? "block" : "none";
  icon.classList.toggle("fa-chevron-down", !isCollapsed);
  icon.classList.toggle("fa-chevron-up", isCollapsed);
});

// CLOSE panel
closeBtn.addEventListener("click", () => {
  panel.style.display = "none";
});

// DRAGGABLE header
let offsetX,
  offsetY,
  dragging = false;

header.addEventListener("mousedown", (e) => {
  dragging = true;
  offsetX = e.clientX - panel.offsetLeft;
  offsetY = e.clientY - panel.offsetTop;
  header.classList.remove("grab");
  header.classList.add("grabbing");
});

document.addEventListener("mousemove", (e) => {
  if (!dragging) return;
  panel.style.left = `${e.clientX - offsetX}px`;
  panel.style.top = `${e.clientY - offsetY}px`;
  panel.style.bottom = "auto";
});

document.addEventListener("mouseup", () => {
  if (dragging) {
    dragging = false;
    header.classList.add("grab");
    header.classList.remove("grabbing");
    localStorage.setItem(
      "panelPosition",
      JSON.stringify({
        left: panel.style.left,
        top: panel.style.top,
      })
    );
  }
});

// Restore saved position
window.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem("panelPosition");
  if (saved) {
    const { left, top } = JSON.parse(saved);
    panel.style.left = left;
    panel.style.top = top;
    panel.style.bottom = "auto";
  }
});

// RESIZABLE bottom
resizeHandle.addEventListener("mousedown", function (e) {
  e.preventDefault();
  const startY = e.clientY;
  const startHeight = panel.offsetHeight;

  const resize = (e) => {
    const newHeight = startHeight + (e.clientY - startY);
    panel.style.height = newHeight + "px";
  };

  const stop = () => {
    window.removeEventListener("mousemove", resize);
    window.removeEventListener("mouseup", stop);
  };

  window.addEventListener("mousemove", resize);
  window.addEventListener("mouseup", stop);
});
