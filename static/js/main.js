document.addEventListener("DOMContentLoaded", function(){
  const startBtn = document.getElementById("startBtn");
  const sessionArea = document.getElementById("sessionArea");
  const sessionLink = document.getElementById("sessionLink");
  const adminVideo = document.getElementById("adminVideo");
  const vol = document.getElementById("vol");
  const fsBtn = document.getElementById("fsBtn");

  startBtn && startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    startBtn.textContent = "Creating...";
    try {
      const res = await fetch("/start-session", { method: "POST" });
      if (!res.ok) throw new Error("Failed to create session");
      const data = await res.json();
      sessionArea.classList.remove("hidden");
      sessionLink.href = data.userurl;
      sessionLink.textContent = data.userurl;
      startBtn.textContent = "STARTED";
    } catch (err) {
      alert("Error creating session: " + err.message);
      startBtn.disabled = false;
      startBtn.textContent = "START SESSION";
    }
  });

  vol && vol.addEventListener("input", () => {
    if (adminVideo) adminVideo.volume = vol.value;
  });

  fsBtn && fsBtn.addEventListener("click", () => {
    if (adminVideo.requestFullscreen) adminVideo.requestFullscreen();
    else if (adminVideo.webkitEnterFullscreen) adminVideo.webkitEnterFullscreen();
  });
});
