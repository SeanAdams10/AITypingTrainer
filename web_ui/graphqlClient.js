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
 * Save a category (create or update)
 * @param {object} category - Category object with categoryId and categoryName
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function saveCategory(category) {
  const query = `
    mutation {
      saveCategory(category: { categoryId: "${category.categoryId}", categoryName: "${category.categoryName}" }) {
        ok
        error
      }
    }
  `;
  const response = await fetch(API_URL, query);
  const data = await response.json();
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }
  return data.data.saveCategory;
}

/**
 * Save a snippet (create or update)
 * @param {object} snippet - Snippet object with snippetId, categoryId, snippetName, content
 * @returns {Promise<Object>} - Result with success/error info
 */
export async function saveSnippet(snippet) {
  const query = `
    mutation {
      saveSnippet(snippet: { snippetId: "${snippet.snippetId}", categoryId: "${snippet.categoryId}", snippetName: "${snippet.snippetName}", content: "${snippet.content.replace(/"/g, '\\"')}" }) {
        ok
        error
      }
    }
  `;
  const response = await fetch(API_URL, query);
  const data = await response.json();
  if (data.errors) {
    throw new Error(data.errors[0].message);
  }
  return data.data.saveSnippet;
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
