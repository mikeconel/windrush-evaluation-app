// form.js - Critical Fixes
document.addEventListener('DOMContentLoaded', function() {
    const formPages = Array.from(document.querySelectorAll('.question-section'));
    const progressBar = document.getElementById('formProgress');
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    const submitBtn = document.querySelector('.submit-btn');
    let currentPage = 0;

    // Initialize form
    function initForm() {
        // Hide all pages except first
        formPages.forEach((page, index) => {
            page.style.display = index === 0 ? 'block' : 'none';
        });
        updateButtonStates();
    }

    // Update button states
    function updateButtonStates() {
        prevBtn.disabled = currentPage === 0;
        nextBtn.disabled = currentPage === formPages.length - 1;
        submitBtn.style.display = currentPage === formPages.length - 1 ? 'block' : 'none';
    }

    // Validate current page
    function validatePage() {
        const currentPageEl = formPages[currentPage];
        const inputs = currentPageEl.querySelectorAll('input, select, textarea');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.checkValidity()) {
                input.reportValidity();
                isValid = false;
            }
        });

        // Special validation for age
        const ageInput = currentPageEl.querySelector('[name="age"]');
        if (ageInput && (ageInput.value < 18 || ageInput.value > 100)) {
            ageInput.setCustomValidity('Must be 18-100');
            ageInput.reportValidity();
            isValid = false;
        }

        return isValid;
    }

    // Navigation handlers
    nextBtn.addEventListener('click', () => {
        if (validatePage()) {
            if (currentPage < formPages.length - 1) {
                formPages[currentPage].style.display = 'none';
                currentPage++;
                formPages[currentPage].style.display = 'block';
                updateButtonStates();
                updateProgress();
            }
        }
    });

    prevBtn.addEventListener('click', () => {
        if (currentPage > 0) {
            formPages[currentPage].style.display = 'none';
            currentPage--;
            formPages[currentPage].style.display = 'block';
            updateButtonStates();
            updateProgress();
        }
    });

    // Progress bar
    function updateProgress() {
        const progress = ((currentPage + 1) / formPages.length) * 100;
        progressBar.style.width = `${progress}%`;
    }

    // Start form
    initForm();
});

/*document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('.question-section');
    const progressBar = document.getElementById('formProgress');
    let currentSection = 0;

    function showSection(index) {
        sections.forEach((section, i) => {
            section.classList.toggle('active', i === index);
        });
        
        document.querySelector('.prev-btn').style.display = 
            index === 0 ? 'none' : 'inline-block';
        document.querySelector('.next-btn').style.display = 
            index === sections.length - 1 ? 'none' : 'inline-block';
        document.querySelector('.submit-btn').style.display = 
            index === sections.length - 1 ? 'inline-block' : 'none';
    }

    function updateProgress() {
        const progress = (currentSection + 1) / sections.length * 100;
        progressBar.style.width = `${progress}%`;
    }

    // Initialize form
    showSection(currentSection);
    updateProgress();

    // Navigation handlers
    document.querySelector('.next-btn').addEventListener('click', () => {
        if (currentSection < sections.length - 1) {
            currentSection++;
            showSection(currentSection);
            updateProgress();
        }
    });

    document.querySelector('.prev-btn').addEventListener('click', () => {
        if (currentSection > 0) {
            currentSection--;
            showSection(currentSection);
            updateProgress();
        }
    });
}); */