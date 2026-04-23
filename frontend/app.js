const routeData = {
  paths: [
    { traffic: "h1 -> h3", path: "s1 -> s2 -> s3" },
    { traffic: "h1 -> h4", path: "s1 -> s2 -> s3" },
    { traffic: "h2 -> h3", path: "s1 -> s2 -> s3" },
    { traffic: "h2 -> h4", path: "s1 -> s2 -> s3" },
    { traffic: "h3 -> h1", path: "s3 -> s2 -> s1" },
    { traffic: "h4 -> h2", path: "s3 -> s2 -> s1" },
    { traffic: "h1 -> h2", path: "s1" },
    { traffic: "h3 -> h4", path: "s3" }
  ],
  flows: [
    { switchName: "s1", summary: "h1->1, h2->2, h3->3, h4->3" },
    { switchName: "s2", summary: "h1->1, h2->1, h3->2, h4->2" },
    { switchName: "s3", summary: "h1->3, h2->3, h3->1, h4->2" }
  ]
};

function renderList(targetId, items, titleKey, subtitleKey) {
  const container = document.getElementById(targetId);
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.style.animation = `rise 0.5s ease forwards ${index * 120}ms`;
    row.innerHTML = `
      <div class="item-title">${item[titleKey]}</div>
      <div class="item-subtitle">${item[subtitleKey]}</div>
    `;
    container.appendChild(row);
  });
}

renderList("path-list", routeData.paths, "traffic", "path");
renderList("flow-list", routeData.flows, "switchName", "summary");
