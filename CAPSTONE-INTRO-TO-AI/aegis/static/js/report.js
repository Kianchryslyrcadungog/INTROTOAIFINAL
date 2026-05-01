/**
 * Aegis — Report Page JavaScript
 * Handles form validation, tag insertion, API call, and loading states
 */

const descInput = document.getElementById('description');
const charCount = document.getElementById('charCount');
const submitBtn = document.getElementById('submitBtn');
const loadingState = document.getElementById('loadingState');
const errorMsg = document.getElementById('errorMsg');
const errorText = document.getElementById('errorText');

// --- Character counter ---
descInput.addEventListener('input', () => {
  const len = descInput.value.length;
  charCount.textContent = len;
  if (len > 900) {
    charCount.style.color = '#ef4444';
  } else if (len > 700) {
    charCount.style.color = '#f59e0b';
  } else {
    charCount.style.color = '';
  }
});

// --- Quick tag buttons ---
document.querySelectorAll('.tag-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tag = btn.dataset.tag;
    const current = descInput.value.trim();
    descInput.value = current ? current + ' ' + tag : tag;
    descInput.dispatchEvent(new Event('input'));
    descInput.focus();

    // Visual feedback
    btn.style.background = 'var(--accent-blue-dim)';
    btn.style.borderColor = 'rgba(59,130,246,0.4)';
    btn.style.color = 'var(--accent-blue)';
    setTimeout(() => {
      btn.style.background = '';
      btn.style.borderColor = '';
      btn.style.color = '';
    }, 800);
  });
});

// --- Loading step animator ---
function animateLoadingSteps() {
  const step1 = document.getElementById('step1');
  const step2 = document.getElementById('step2');
  const step3 = document.getElementById('step3');

  // Step 1 starts active immediately
  step1.classList.add('active');

  setTimeout(() => {
    step1.classList.remove('active');
    step1.classList.add('done');
    step1.textContent = 'ML Classification Complete';
    step2.classList.add('active');
  }, 800);

  setTimeout(() => {
    step2.classList.remove('active');
    step2.classList.add('done');
    step2.textContent = 'Risk Level Determined';
    step3.classList.add('active');
  }, 1500);

  setTimeout(() => {
    step3.classList.remove('active');
    step3.classList.add('done');
    step3.textContent = 'Recommendations Ready';
  }, 2200);
}

// --- Main submit function ---
async function submitReport() {
  const description = descInput.value.trim();
  const location = document.getElementById('location').value;

  // Validation
  if (!description) {
    showError('Please describe the incident before submitting.');
    descInput.focus();
    return;
  }

  if (description.length < 10) {
    showError('Please provide more detail about the incident (at least 10 characters).');
    descInput.focus();
    return;
  }

  if (!location) {
    showError('Please select the incident location.');
    return;
  }

  hideError();
  setLoading(true);
  animateLoadingSteps();

  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description, location })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || 'Analysis failed');
    }

    const data = await response.json();

    // Store result in sessionStorage for the result page
    sessionStorage.setItem('aegisResult', JSON.stringify(data));

    // Small delay to let loading animation finish
    await sleep(2600);

    // Navigate to result page
    window.location.href = '/result';

  } catch (error) {
    setLoading(false);
    showError('Error: ' + error.message + '. Please try again.');
  }
}

// --- Helper: show/hide error ---
function showError(message) {
  errorText.textContent = message;
  errorMsg.style.display = 'flex';
  errorMsg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  errorMsg.style.display = 'none';
}

// --- Helper: toggle loading state ---
function setLoading(isLoading) {
  submitBtn.style.display = isLoading ? 'none' : 'flex';
  loadingState.style.display = isLoading ? 'block' : 'none';
}

// --- Helper: sleep ---
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Allow Enter key in textarea with Ctrl+Enter to submit
descInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    submitReport();
  }
});
