const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const fileInfo = document.getElementById('file-info');
const errorBox = document.getElementById('error-box');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const results = document.getElementById('results');
const extractedTextEl = document.getElementById('extracted-text');
const statsEl = document.getElementById('stats');
const suggestionsEl = document.getElementById('suggestions');

// --- Drag & drop wiring ---
['dragenter', 'dragover'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', (e) => {
  const files = e.dataTransfer.files;
  if (files && files.length > 0) {
    handleFile(files[0]);
  }
});

// Clicking anywhere on the dropzone (except the button, which also works) opens the picker
dropzone.addEventListener('click', (e) => {
  fileInput.click();
});

browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    handleFile(fileInput.files[0]);
  }
});

function resetUI() {
  errorBox.classList.add('hidden');
  errorBox.textContent = '';
  results.classList.add('hidden');
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

function showFileInfo(file) {
  const sizeKb = (file.size / 1024).toFixed(1);
  fileInfo.textContent = `${file.name} — ${sizeKb} KB`;
  fileInfo.classList.remove('hidden');
}

async function handleFile(file) {
  resetUI();
  showFileInfo(file);

  const isImage = file.type.startsWith('image/');
  loadingText.textContent = isImage ? 'Running OCR on image…' : 'Extracting text from PDF…';
  loading.classList.remove('hidden');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
    });

    let data;
    try {
      data = await response.json();
    } catch (parseErr) {
      throw new Error('The server returned an unexpected response.');
    }

    if (!response.ok || !data.success) {
      throw new Error(data.error || `Request failed with status ${response.status}.`);
    }

    renderResults(data);
  } catch (err) {
    showError(err.message || 'Something went wrong while analyzing this file.');
  } finally {
    loading.classList.add('hidden');
  }
}

function renderResults(data) {
  extractedTextEl.textContent = data.extracted_text && data.extracted_text.trim()
    ? data.extracted_text
    : '(No text could be extracted from this file.)';

  const a = data.analysis;
  statsEl.innerHTML = `
    <div class="stat"><span class="value">${a.word_count}</span><span class="label">Words</span></div>
    <div class="stat"><span class="value">${a.hashtag_count}</span><span class="label">Hashtags</span></div>
    <div class="stat"><span class="value">${a.mention_count}</span><span class="label">Mentions</span></div>
    <div class="stat"><span class="value">${a.emoji_count}</span><span class="label">Emojis</span></div>
  `;

  suggestionsEl.innerHTML = '';
  a.suggestions.forEach((s) => {
    const li = document.createElement('li');
    li.textContent = s;
    suggestionsEl.appendChild(li);
  });

  results.classList.remove('hidden');
}
