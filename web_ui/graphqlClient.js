/**
 * GraphQL client for communicating with the Snippets Library API
 * Handles all data operations for the Web UI
 */

// Base URL for GraphQL API
const API_URL = '/api/library_graphql';

/**
 * Generic function to make GraphQL requests
 * @param {string} url - API endpoint
 * @param {string} query - GraphQL query
 * @param {Object} variables - Query variables
 * @returns {Promise<Object>} - Response data
 */
async function fetch(url, query, variables = {}) {
  const response = await window.fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      variables,
    }),
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  return response;
}

/**
 * Fetch all categories
 * @returns {Promise<Array>} - List of categories
 */
export async function fetchCategories() {
  const query = `{
    categories {
      categoryId
      categoryName
    }
  }`;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.categories || [];
}

/**
 * Fetch snippets for a specific category
 * @param {number} categoryId - Category ID
 * @returns {Promise<Array>} - List of snippets
 */
export async function fetchSnippets(categoryId) {
  const query = `{
    snippets(categoryId: ${categoryId}) {
      snippetId
      categoryId
      snippetName
      content
    }
  }`;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.snippets || [];
}

/**
 * Add a new category
 * @param {string} categoryName - New category name
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function addCategory(categoryName) {
  const query = `
    mutation {
      createCategory(categoryName: "${categoryName}") {
        category {
          categoryId
          categoryName
        }
        ok
        error
      }
    }
  `;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.createCategory;
}

/**
 * Update an existing category
 * @param {number} categoryId - Category ID
 * @param {string} newName - New category name
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function updateCategory(categoryId, newName) {
  const query = `
    mutation {
      renameCategory(categoryId: ${categoryId}, categoryName: "${newName}") {
        ok
        error
      }
    }
  `;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.renameCategory;
}

/**
 * Delete a category
 * @param {number} categoryId - Category ID
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function deleteCategory(categoryId) {
  const query = `
    mutation {
      deleteCategory(categoryId: ${categoryId}) {
        ok
        error
      }
    }
  `;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.deleteCategory;
}

/**
 * Add a new snippet
 * @param {number} categoryId - Category ID
 * @param {string} snippetName - New snippet name
 * @param {string} content - Snippet content
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function addSnippet(categoryId, snippetName, content) {
  const query = `
    mutation {
      createSnippet(
        categoryId: ${categoryId},
        snippetName: "${snippetName}",
        content: "${content.replace(/"/g, '\\"')}"
      ) {
        snippet {
          snippetId
          categoryId
          snippetName
          content
        }
        ok
        error
      }
    }
  `;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.createSnippet;
}

/**
 * Update an existing snippet
 * @param {number} snippetId - Snippet ID
 * @param {string} snippetName - New snippet name
 * @param {string} content - New snippet content
 * @param {number|null} categoryId - Optional new category ID
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function updateSnippet(snippetId, snippetName, content, categoryId = null) {
  const categoryParam = categoryId ? `categoryId: ${categoryId},` : '';
  
  const query = `
    mutation {
      editSnippet(
        snippetId: ${snippetId},
        ${categoryParam}
        snippetName: "${snippetName}",
        content: "${content.replace(/"/g, '\\"')}"
      ) {
        ok
        error
      }
    }
  `;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.editSnippet;
}

/**
 * Delete a snippet
 * @param {number} snippetId - Snippet ID
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function deleteSnippet(snippetId) {
  const query = `
    mutation {
      deleteSnippet(snippetId: ${snippetId}) {
        ok
        error
      }
    }
  `;

  const response = await fetch(API_URL, query);
  const data = await response.json();

  // Handle GraphQL errors
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }

  return data.data.deleteSnippet;
}
