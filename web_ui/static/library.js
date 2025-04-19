let currentCategoryId = null;

function showError(id, message) {
    const div = document.getElementById(id);
    if (div) {
        div.textContent = message;
        div.classList.remove('d-none');
    }
}
function hideError(id) {
    const div = document.getElementById(id);
    if (div) {
        div.textContent = '';
        div.classList.add('d-none');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Hide errors on modal show
    const addCategoryModal = document.getElementById('addCategoryModal');
    if (addCategoryModal) {
        addCategoryModal.addEventListener('show.bs.modal', function() { hideError('addCategoryError'); });
    }
    const renameCategoryModal = document.getElementById('renameCategoryModal');
    if (renameCategoryModal) {
        renameCategoryModal.addEventListener('show.bs.modal', function() { hideError('renameCategoryError'); });
    }
    const addSnippetModal = document.getElementById('addSnippetModal');
    if (addSnippetModal) {
        addSnippetModal.addEventListener('show.bs.modal', function() { hideError('addSnippetError'); });
    }
    // Add Category Form Handler
    document.getElementById('addCategoryForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        hideError('addCategoryError');
        const categoryName = document.getElementById('categoryName').value;
        try {
            const response = await fetch('/api/library/category', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: categoryName })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showError('addCategoryError', data.message || 'Failed to add category');
                return;
            }
            window.location.reload();
        } catch (error) {
            showError('addCategoryError', error.message);
        }
    });

    // Rename Category Handlers
    document.querySelectorAll('.rename-category').forEach(button => {
        button.addEventListener('click', function() {
            const categoryId = this.dataset.categoryId;
            const categoryName = this.dataset.categoryName;
            document.getElementById('renameCategoryId').value = categoryId;
            document.getElementById('newCategoryName').value = categoryName;
            new bootstrap.Modal(document.getElementById('renameCategoryModal')).show();
        });
    });

    // Rename Category Form Handler
    document.getElementById('renameCategoryForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        hideError('renameCategoryError');
        const categoryId = document.getElementById('renameCategoryId').value;
        const newName = document.getElementById('newCategoryName').value;
        try {
            const response = await fetch(`/api/library/category/${categoryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: newName })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showError('renameCategoryError', data.message || 'Failed to rename category');
                return;
            }
            window.location.reload();
        } catch (error) {
            showError('renameCategoryError', error.message);
        }
    });

    // Select Category Handlers
    // Delete Category Handler
    document.querySelectorAll('.delete-category').forEach(button => {
        button.addEventListener('click', async function() {
            const categoryId = this.dataset.categoryId;
            if (!confirm('Delete this category and all its snippets? This cannot be undone!')) return;
            try {
                const response = await fetch(`/api/library/category/${categoryId}`, {
                    method: 'DELETE',
                });
                if (!response.ok) throw new Error('Failed to delete category');
                window.location.reload();
            } catch (error) {
                alert('Error deleting category: ' + error.message);
            }
        });
    });

    document.querySelectorAll('.select-category').forEach(button => {
        button.addEventListener('click', async function() {
            currentCategoryId = this.dataset.categoryId;
            document.getElementById('addSnippetBtn').disabled = false;
            document.getElementById('snippetCategoryId').value = currentCategoryId;
            
            // Highlight selected category
            document.querySelectorAll('.list-group-item').forEach(item => {
                item.classList.remove('active');
            });
            this.closest('.list-group-item').classList.add('active');
            
            // Load snippets for this category
            await loadSnippets(currentCategoryId);
        });
    });

    // Add Snippet Form Handler
    document.getElementById('addSnippetForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        hideError('addSnippetError');
        const snippetName = document.getElementById('snippetName').value;
        const snippetText = document.getElementById('snippetText').value;
        const categoryId = document.getElementById('snippetCategoryId').value;
        try {
            const response = await fetch('/api/library/snippet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: snippetName, text: snippetText, category_id: categoryId })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showError('addSnippetError', data.message || 'Failed to add snippet');
                return;
            }
            window.location.reload();
        } catch (error) {
            showError('addSnippetError', error.message);
        }
    });
        
        try {
            const response = await fetch('/api/library/snippets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    categoryId: parseInt(categoryId),
                    name: snippetName,
                    text: snippetText
                })
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || 'Failed to add snippet');
            }
            
            // Show success message if name was modified
            if (data.snippet_name !== snippetName) {
                alert(`Snippet added successfully as "${data.snippet_name}"`);
            }
            
            // Close modal and reload snippets
            bootstrap.Modal.getInstance(document.getElementById('addSnippetModal')).hide();
            document.getElementById('snippetName').value = '';
            document.getElementById('snippetText').value = '';
            await loadSnippets(currentCategoryId);
        } catch (error) {
            alert('Error adding snippet: ' + error.message);
        }
    });

    // File Upload Handler
    document.getElementById('snippetFile').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('snippetText').value = e.target.result;
            };
            reader.readAsText(file);
        }
    });

    // Snippet Search Handler
    document.getElementById('snippetSearch').addEventListener('input', debounce(async function() {
        if (currentCategoryId) {
            await loadSnippets(currentCategoryId, this.value);
        }
    }, 300));
});

async function loadSnippets(categoryId, searchTerm = '') {
    try {
        const response = await fetch(`/api/library/snippets/${categoryId}?search=${encodeURIComponent(searchTerm)}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to load snippets');
        }
        
        const snippets = await response.json();
        const snippetsList = document.getElementById('snippetsList');
        snippetsList.innerHTML = '';
        
        if (snippets.length === 0) {
            snippetsList.innerHTML = '<div class="list-group-item">No snippets found</div>';
            return;
        }
        
        snippets.forEach(snippet => {
            // We're expecting snippet_id and snippet_name fields based on our API
            if (!snippet.snippet_id) {
                console.error('Missing snippet_id in response:', snippet);
                return;
            }
            
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            
            // Use snippet_name
            const displayName = snippet.snippet_name || 'Untitled Snippet';
            
            item.innerHTML = `
                <span>${displayName}</span>
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary view-snippet" data-snippet-id="${snippet.snippet_id}">
                        View
                    </button>
                    <button class="btn btn-sm btn-outline-success start-drill" data-snippet-id="${snippet.snippet_id}">
                        Start Drill
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-snippet" data-snippet-id="${snippet.snippet_id}" data-snippet-name="${displayName}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            
            // Add click handlers for the buttons
            const viewBtn = item.querySelector('.view-snippet');
            const startBtn = item.querySelector('.start-drill');
            const deleteBtn = item.querySelector('.delete-snippet');
            
            viewBtn.addEventListener('click', () => viewSnippet(snippet.snippet_id));
            startBtn.addEventListener('click', () => {
                window.location.href = `/configure-drill?snippet=${snippet.snippet_id}`;
            });
            deleteBtn.addEventListener('click', () => confirmDeleteSnippet(snippet.snippet_id, displayName));
            
            snippetsList.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading snippets:', error);
        const snippetsList = document.getElementById('snippetsList');
        snippetsList.innerHTML = `<div class="list-group-item text-danger">Error: ${error.message}</div>`;
    }
}

async function viewSnippet(snippetId) {
    try {
        const response = await fetch(`/api/library/snippet_parts/${snippetId}`);
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to load snippet');
        }
        
        const snippet = await response.json();
        
        // Update to use consistent field names
        document.getElementById('viewSnippetName').textContent = snippet.snippet_name;
        document.getElementById('viewSnippetText').textContent = snippet.text;
        
        new bootstrap.Modal(document.getElementById('viewSnippetModal')).show();
    } catch (error) {
        console.error('Error in viewSnippet:', error);
        alert('Error loading snippet: ' + error.message);
    }
}

async function confirmDeleteSnippet(snippetId, snippetName) {
    if (confirm(`Are you sure you want to delete "${snippetName}"? This will also delete all practice sessions for this snippet.`)) {
        try {
            const response = await fetch(`/api/snippets/${snippetId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to delete snippet');
            }
            
            // Show success message
            alert(data.message || 'Snippet deleted successfully');
            
            // Reload snippets for the current category
            await loadSnippets(currentCategoryId);
        } catch (error) {
            console.error('Error deleting snippet:', error);
            alert('Error deleting snippet: ' + error.message);
        }
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
