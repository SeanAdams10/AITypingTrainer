let currentCategoryId = null;

// Helper functions for error handling
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

// Debounce function to prevent excessive API calls during search
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// API client with robust error handling
const apiClient = {
    // Base endpoint URLs
    endpoints: {
        categories: '/api/categories',
        snippets: '/api/snippets'
    },

    // HTTP methods
    async get(url, params = {}) {
        try {
            // Add query parameters if provided
            const queryParams = new URLSearchParams(params).toString();
            const fullUrl = queryParams ? `${url}?${queryParams}` : url;

            const response = await fetch(fullUrl);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP error ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API GET error for ${url}:`, error);
            return null; // Return null to indicate failure but not crash
        }
    },

    async post(url, data) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const responseData = await response.json();
            if (!response.ok || responseData.success === false) {
                throw new Error(responseData.message || `HTTP error ${response.status}`);
            }
            return responseData;
        } catch (error) {
            console.error(`API POST error for ${url}:`, error);
            throw error; // Rethrow for critical operations
        }
    },

    async put(url, data) {
        try {
            const response = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const responseData = await response.json();
            if (!response.ok || responseData.success === false) {
                throw new Error(responseData.message || `HTTP error ${response.status}`);
            }
            return responseData;
        } catch (error) {
            console.error(`API PUT error for ${url}:`, error);
            throw error; // Rethrow for critical operations
        }
    },

    async delete(url) {
        try {
            const response = await fetch(url, { method: 'DELETE' });
            const responseData = await response.json();
            if (!response.ok || responseData.success === false) {
                throw new Error(responseData.message || `HTTP error ${response.status}`);
            }
            return responseData;
        } catch (error) {
            console.error(`API DELETE error for ${url}:`, error);
            throw error; // Rethrow for critical operations
        }
    },

    // Category operations
    async getCategories() {
        const data = await this.get(this.endpoints.categories);
        return data && data.success ? data.categories : [];
    },

    async addCategory(name) {
        return await this.post(this.endpoints.categories, { name });
    },

    async updateCategory(categoryId, name) {
        return await this.put(`${this.endpoints.categories}/${categoryId}`, { name });
    },

    async deleteCategory(categoryId) {
        return await this.delete(`${this.endpoints.categories}/${categoryId}`);
    },

    // Snippet operations
    async getSnippets(categoryId, search = '') {
        const data = await this.get(this.endpoints.snippets, { category_id: categoryId });
        if (!data) return []; // Handle null response

        // If data is an array, it's already the snippets list
        const snippets = Array.isArray(data) ? data :
                       (data.snippets || []);

        // Filter by search term if provided
        if (search) {
            const lowerSearch = search.toLowerCase();
            return snippets.filter(s =>
                s.snippet_name.toLowerCase().includes(lowerSearch));
        }
        return snippets;
    },

    async getSnippetContent(snippetId) {
        const data = await this.get(`${this.endpoints.snippets}/${snippetId}`);
        return data ? (data.content || '') : '';
    },

    async addSnippet(categoryId, name, content) {
        return await this.post(this.endpoints.snippets, {
            category_id: categoryId,
            snippet_name: name,
            content: content
        });
    },

    async updateSnippet(snippetId, name, content, categoryId) {
        const data = { snippet_name: name, content: content };
        if (categoryId) data.category_id = categoryId;
        return await this.put(`${this.endpoints.snippets}/${snippetId}`, data);
    },

    async deleteSnippet(snippetId) {
        return await this.delete(`${this.endpoints.snippets}/${snippetId}`);
    }
};

// Load snippets for a category with optional search filter
async function loadSnippets(categoryId, searchTerm = '') {
    const snippetList = document.getElementById('snippetList');
    if (!snippetList) return;

    snippetList.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Loading snippets...</p></div>';

    try {
        const snippets = await apiClient.getSnippets(categoryId, searchTerm);

        if (snippets.length === 0) {
            snippetList.innerHTML = '<div class="alert alert-info">No snippets found.</div>';
            return;
        }

        // Build snippet list HTML
        let html = '';
        snippets.forEach(snippet => {
            html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span class="snippet-name" data-snippet-id="${snippet.snippet_id}">${snippet.snippet_name}</span>
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary view-snippet"
                            data-snippet-id="${snippet.snippet_id}"
                            data-snippet-name="${snippet.snippet_name}">
                        View
                    </button>
                    <button class="btn btn-sm btn-outline-success edit-snippet"
                            data-snippet-id="${snippet.snippet_id}"
                            data-snippet-name="${snippet.snippet_name}">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-snippet"
                            data-snippet-id="${snippet.snippet_id}"
                            data-snippet-name="${snippet.snippet_name}">
                        Delete
                    </button>
                </div>
            </div>`;
        });
        snippetList.innerHTML = html;

        // Add event listeners to the new buttons
        snippetList.querySelectorAll('.view-snippet').forEach(btn => {
            btn.addEventListener('click', function() {
                viewSnippet(this.dataset.snippetId);
            });
        });

        snippetList.querySelectorAll('.edit-snippet').forEach(btn => {
            btn.addEventListener('click', function() {
                editSnippet(this.dataset.snippetId);
            });
        });

        snippetList.querySelectorAll('.delete-snippet').forEach(btn => {
            btn.addEventListener('click', function() {
                confirmDeleteSnippet(this.dataset.snippetId, this.dataset.snippetName);
            });
        });
    } catch (error) {
        snippetList.innerHTML = `<div class="alert alert-danger">Error loading snippets: ${error.message}</div>`;
    }
}

// View a snippet's full content
async function viewSnippet(snippetId) {
    const modal = document.getElementById('viewSnippetModal');
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('.modal-body');

    modalTitle.textContent = 'Loading...';
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';

    new bootstrap.Modal(modal).show();

    try {
        const content = await apiClient.getSnippetContent(snippetId);
        const snippets = await apiClient.getSnippets(currentCategoryId);
        const snippet = snippets.find(s => s.snippet_id == snippetId);

        modalTitle.textContent = snippet ? snippet.snippet_name : 'View Snippet';
        modalBody.innerHTML = `<pre class="bg-light p-3 rounded">${content}</pre>`;
    } catch (error) {
        modalBody.innerHTML = `<div class="alert alert-danger">Error loading snippet: ${error.message}</div>`;
    }
}

// Edit a snippet
async function editSnippet(snippetId) {
    try {
        const snippets = await apiClient.getSnippets(currentCategoryId);
        const snippet = snippets.find(s => s.snippet_id == snippetId);
        const content = await apiClient.getSnippetContent(snippetId);

        if (!snippet) throw new Error('Snippet not found');

        const modal = document.getElementById('editSnippetModal');
        modal.querySelector('#editSnippetId').value = snippetId;
        modal.querySelector('#editSnippetName').value = snippet.snippet_name;
        modal.querySelector('#editSnippetText').value = content;

        new bootstrap.Modal(modal).show();
    } catch (error) {
        alert('Error loading snippet for editing: ' + error.message);
    }
}

// Confirm and delete a snippet
async function confirmDeleteSnippet(snippetId, snippetName) {
    if (!confirm(`Delete snippet "${snippetName}"? This cannot be undone!`)) return;

    try {
        await apiClient.deleteSnippet(snippetId);
        await loadSnippets(currentCategoryId);
    } catch (error) {
        alert('Error deleting snippet: ' + error.message);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Hide errors on modal show
    const addCategoryModal = document.getElementById('addCategoryModal');
    if (addCategoryModal) {
        addCategoryModal.addEventListener('show.bs.modal', function() {
            hideError('addCategoryError');
        });
    }

    const renameCategoryModal = document.getElementById('renameCategoryModal');
    if (renameCategoryModal) {
        renameCategoryModal.addEventListener('show.bs.modal', function() {
            hideError('renameCategoryError');
        });
    }

    const addSnippetModal = document.getElementById('addSnippetModal');
    if (addSnippetModal) {
        addSnippetModal.addEventListener('show.bs.modal', function() {
            hideError('addSnippetError');
        });
    }

    const editSnippetModal = document.getElementById('editSnippetModal');
    if (editSnippetModal) {
        editSnippetModal.addEventListener('show.bs.modal', function() {
            hideError('editSnippetError');
        });
    }

    // Add Category Form
    const addCategoryForm = document.getElementById('addCategoryForm');
    if (addCategoryForm) {
        addCategoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            hideError('addCategoryError');
            const categoryName = document.getElementById('categoryName').value;

            try {
                await apiClient.addCategory(categoryName);
                window.location.reload();
            } catch (error) {
                showError('addCategoryError', error.message);
            }
        });
    }

    // Rename Category Buttons
    document.querySelectorAll('.rename-category').forEach(button => {
        button.addEventListener('click', function() {
            const categoryId = this.dataset.categoryId;
            const categoryName = this.dataset.categoryName;
            document.getElementById('renameCategoryId').value = categoryId;
            document.getElementById('newCategoryName').value = categoryName;
            new bootstrap.Modal(document.getElementById('renameCategoryModal')).show();
        });
    });

    // Rename Category Form
    const renameCategoryForm = document.getElementById('renameCategoryForm');
    if (renameCategoryForm) {
        renameCategoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            hideError('renameCategoryError');
            const categoryId = document.getElementById('renameCategoryId').value;
            const newName = document.getElementById('newCategoryName').value;

            try {
                await apiClient.updateCategory(categoryId, newName);
                window.location.reload();
            } catch (error) {
                showError('renameCategoryError', error.message);
            }
        });
    }

    // Delete Category Buttons
    document.querySelectorAll('.delete-category').forEach(button => {
        button.addEventListener('click', async function() {
            const categoryId = this.dataset.categoryId;
            if (!confirm('Delete this category and all its snippets? This cannot be undone!')) return;

            try {
                await apiClient.deleteCategory(categoryId);
                window.location.reload();
            } catch (error) {
                alert('Error deleting category: ' + error.message);
            }
        });
    });

    // Select Category Buttons
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

    // Add Snippet Form
    const addSnippetForm = document.getElementById('addSnippetForm');
    if (addSnippetForm) {
        addSnippetForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            hideError('addSnippetError');
            const snippetName = document.getElementById('snippetName').value;
            const snippetText = document.getElementById('snippetText').value;
            const categoryId = document.getElementById('snippetCategoryId').value;

            try {
                await apiClient.addSnippet(categoryId, snippetName, snippetText);

                // Close modal and reset form
                const modal = bootstrap.Modal.getInstance(document.getElementById('addSnippetModal'));
                if (modal) modal.hide();

                document.getElementById('snippetName').value = '';
                document.getElementById('snippetText').value = '';

                // Reload snippets
                await loadSnippets(currentCategoryId);
            } catch (error) {
                showError('addSnippetError', error.message);
            }
        });
    }

    // File Upload Control
    const snippetFile = document.getElementById('snippetFile');
    if (snippetFile) {
        snippetFile.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('snippetText').value = e.target.result;
                };
                reader.readAsText(file);
            }
        });
    }

    // Snippet Search
    const snippetSearch = document.getElementById('snippetSearch');
    if (snippetSearch) {
        snippetSearch.addEventListener('input', debounce(function() {
            if (currentCategoryId) {
                loadSnippets(currentCategoryId, this.value);
            }
        }, 300));
    }

    // Edit Snippet Form
    const editForm = document.getElementById('editSnippetForm');
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            hideError('editSnippetError');

            const snippetId = document.getElementById('editSnippetId').value;
            const snippetName = document.getElementById('editSnippetName').value;
            const snippetText = document.getElementById('editSnippetText').value;

            try {
                await apiClient.updateSnippet(snippetId, snippetName, snippetText);

                // Close modal and reload snippets
                const modal = bootstrap.Modal.getInstance(document.getElementById('editSnippetModal'));
                if (modal) modal.hide();

                await loadSnippets(currentCategoryId);
            } catch (error) {
                showError('editSnippetError', error.message);
            }
        });
    }
});
