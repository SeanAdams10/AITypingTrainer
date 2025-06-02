// Main entry point for the Snippets Library Web UI
// React + TypeScript + Material UI
import React, { useState, useEffect } from 'react';
import { Container, Grid, Paper, Typography, Snackbar, Alert, Box } from '@mui/material';
import CategoryList from './components/CategoryList';
import SnippetList from './components/SnippetList';
import CategoryEditorModal from './components/CategoryEditorModal';
import SnippetEditorModal from './components/SnippetEditorModal';
import ConfirmDialog from './components/ConfirmDialog';
import { 
  fetchCategories, 
  fetchSnippets, 
  deleteCategory, 
  deleteSnippet, 
  saveCategory, 
  saveSnippet 
} from './graphqlClient';

// TypeScript interfaces for our data models
interface Category {
  categoryId: number;
  categoryName: string;
}

interface Snippet {
  snippetId: number;
  categoryId: number;
  snippetName: string;
  content: string;
}

const LibraryApp: React.FC = () => {
  // State for data
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  
  // State for selected items
  const [selectedSnippet, setSelectedSnippet] = useState<Snippet | null>(null);
  
  // State for modals
  const [openCatModal, setOpenCatModal] = useState(false);
  const [openSnipModal, setOpenSnipModal] = useState(false);
  const [catForEdit, setCatForEdit] = useState<Category | null>(null);
  const [snippetForEdit, setSnippetForEdit] = useState<Snippet | null>(null);
  const [viewSnippetMode, setViewSnippetMode] = useState(false);
  
  // State for confirm dialogs
  const [deleteCatConfirm, setDeleteCatConfirm] = useState(false);
  const [deleteSnipConfirm, setDeleteSnipConfirm] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<any>(null);
  
  // State for notifications
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load categories on component mount
  useEffect(() => {
    loadCategories();
  }, []);

  // Load snippets when selected category changes
  useEffect(() => {
    if (selectedCategory) {
      loadSnippets(selectedCategory.categoryId);
    } else {
      setSnippets([]);
    }
  }, [selectedCategory]);

  // Function to load categories from API
  const loadCategories = () => {
    fetchCategories()
      .then(data => {
        setCategories(data);
        // If there are categories but none selected, select the first one
        if (data.length > 0 && !selectedCategory) {
          setSelectedCategory(data[0]);
        }
      })
      .catch(err => handleError(err.message || 'Failed to load categories'));
  };

  // Function to load snippets for a category
  const loadSnippets = (categoryId: number) => {
    fetchSnippets(categoryId)
      .then(setSnippets)
      .catch(err => handleError(err.message || 'Failed to load snippets'));
  };

  // Function to handle errors
  const handleError = (message: string) => {
    setErrorMsg(message);
    setTimeout(() => setErrorMsg(null), 5000); // Auto-dismiss after 5 seconds
  };

  // Function to show success message
  const showSuccess = (message: string) => {
    setSuccessMsg(message);
    setTimeout(() => setSuccessMsg(null), 3000); // Auto-dismiss after 3 seconds
  };

  // Category operations
  const handleAddCategory = () => {
    setCatForEdit(null);
    setOpenCatModal(true);
  };

  const handleEditCategory = (category: Category) => {
    setCatForEdit(category);
    setOpenCatModal(true);
  };

  const handleDeleteCategory = (category: Category) => {
    setItemToDelete(category);
    setDeleteCatConfirm(true);
  };

  const confirmDeleteCategory = async () => {
    if (!itemToDelete) return;
    
    try {
      const result = await deleteCategory(itemToDelete.categoryId);
      if (result.ok) {
        // If the deleted category was selected, clear selection
        if (selectedCategory && selectedCategory.categoryId === itemToDelete.categoryId) {
          setSelectedCategory(null);
        }
        loadCategories();
        showSuccess(`Category '${itemToDelete.categoryName}' deleted successfully`);
      } else {
        handleError(result.error || 'Failed to delete category');
      }
    } catch (error: any) {
      handleError(error.message || 'An error occurred while deleting the category');
    } finally {
      setDeleteCatConfirm(false);
      setItemToDelete(null);
    }
  };

  // Snippet operations
  const handleAddSnippet = () => {
    if (!selectedCategory) {
      handleError('Please select a category first');
      return;
    }
    setSnippetForEdit(null);
    setViewSnippetMode(false);
    setOpenSnipModal(true);
  };

  const handleEditSnippet = (snippet: Snippet) => {
    setSnippetForEdit(snippet);
    setViewSnippetMode(false);
    setOpenSnipModal(true);
  };

  const handleViewSnippet = (snippet: Snippet) => {
    setSnippetForEdit(snippet);
    setViewSnippetMode(true);
    setOpenSnipModal(true);
  };

  const handleDeleteSnippet = (snippet: Snippet) => {
    setItemToDelete(snippet);
    setDeleteSnipConfirm(true);
  };

  const confirmDeleteSnippet = async () => {
    if (!itemToDelete) return;
    
    try {
      const result = await deleteSnippet(itemToDelete.snippetId);
      if (result.ok) {
        if (selectedCategory) {
          loadSnippets(selectedCategory.categoryId);
        }
        showSuccess(`Snippet '${itemToDelete.snippetName}' deleted successfully`);
      } else {
        handleError(result.error || 'Failed to delete snippet');
      }
    } catch (error: any) {
      handleError(error.message || 'An error occurred while deleting the snippet');
    } finally {
      setDeleteSnipConfirm(false);
      setItemToDelete(null);
    }
  };

  // Modal close handlers
  const handleCategoryModalClose = () => {
    setOpenCatModal(false);
    setCatForEdit(null);
    loadCategories();
  };

  const handleSnippetModalClose = () => {
    setOpenSnipModal(false);
    setSnippetForEdit(null);
    setViewSnippetMode(false);
    if (selectedCategory) {
      loadSnippets(selectedCategory.categoryId);
    }
  };

  return (
    <Container maxWidth="xl" sx={{ height: '100vh', padding: 0, position: 'relative' }}>
      <Grid container sx={{ height: '100%' }}>
        <Grid item xs={3} component={Paper} square sx={{ borderRight: 1, borderColor: 'divider' }}>
          <CategoryList
            categories={categories}
            selected={selectedCategory}
            onSelect={setSelectedCategory}
            onAdd={handleAddCategory}
            onEdit={handleEditCategory}
            onDelete={handleDeleteCategory}
            onError={handleError}
          />
        </Grid>
        <Grid item xs={9} component={Paper} square>
          <SnippetList
            snippets={snippets}
            onAdd={handleAddSnippet}
            onEdit={handleEditSnippet}
            onDelete={handleDeleteSnippet}
            onView={handleViewSnippet}
            onError={handleError}
          />
        </Grid>
      </Grid>
      
      {/* Modals */}
      <CategoryEditorModal 
        open={openCatModal} 
        onClose={handleCategoryModalClose} 
        category={catForEdit}
        onError={handleError} 
      />
      
      <SnippetEditorModal 
        open={openSnipModal} 
        onClose={handleSnippetModalClose} 
        categoryId={selectedCategory?.categoryId} 
        snippet={snippetForEdit}
        onError={handleError}
        readOnly={viewSnippetMode}
      />
      
      {/* Confirmation Dialogs */}
      <ConfirmDialog 
        open={deleteCatConfirm} 
        onClose={() => setDeleteCatConfirm(false)}
        onConfirm={confirmDeleteCategory}
        title="Delete Category"
        message={`Are you sure you want to delete '${itemToDelete?.categoryName}'? All snippets in this category will also be deleted.`}
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        confirmButtonColor="error"
      />
      
      <ConfirmDialog 
        open={deleteSnipConfirm} 
        onClose={() => setDeleteSnipConfirm(false)}
        onConfirm={confirmDeleteSnippet}
        title="Delete Snippet"
        message={`Are you sure you want to delete '${itemToDelete?.snippetName}'?`}
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        confirmButtonColor="error"
      />
      
      {/* Notification Snackbars */}
      <Snackbar 
        open={!!errorMsg} 
        autoHideDuration={5000} 
        onClose={() => setErrorMsg(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="error" variant="filled" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      </Snackbar>
      
      <Snackbar 
        open={!!successMsg} 
        autoHideDuration={3000} 
        onClose={() => setSuccessMsg(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" variant="filled" onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default LibraryApp;
