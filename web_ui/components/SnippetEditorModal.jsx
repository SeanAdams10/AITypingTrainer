/**
 * SnippetEditorModal Component - Form dialog for adding/editing snippets
 */
import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  TextField, 
  Button, 
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import PropTypes from 'prop-types';
import { addSnippet, updateSnippet, fetchCategories } from '../graphqlClient';

/**
 * Modal dialog for adding or editing a snippet
 * @param {Object} props - Component props
 * @param {boolean} props.open - Whether the dialog is open
 * @param {Function} props.onClose - Handler for dialog close
 * @param {number} props.categoryId - Current category ID
 * @param {Object} props.snippet - Snippet object (for edit mode, null for add mode)
 * @param {Function} props.onError - Handler for error reporting
 * @param {boolean} props.readOnly - Whether the dialog is in read-only view mode
 */
const SnippetEditorModal = ({ open, onClose, categoryId, snippet, onError, readOnly = false }) => {
  const [name, setName] = useState('');
  const [content, setContent] = useState('');
  const [selectedCategoryId, setSelectedCategoryId] = useState(categoryId || 0);
  const [categories, setCategories] = useState([]);
  const [nameError, setNameError] = useState('');
  const [contentError, setContentError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  
  const isEditMode = Boolean(snippet) && !readOnly;
  const isViewMode = Boolean(snippet) && readOnly;
  const title = isViewMode ? 'View Snippet' : (isEditMode ? 'Edit Snippet' : 'Add Snippet');
  
  // Load categories for the dropdown (only in edit mode)
  useEffect(() => {
    if (open && isEditMode) {
      fetchCategories()
        .then(setCategories)
        .catch(err => onError(err.message || 'Failed to load categories'));
    }
  }, [open, isEditMode, onError]);
  
  // Reset form when dialog opens or snippet changes
  useEffect(() => {
    if (open) {
      if (snippet) {
        setName(snippet.snippetName);
        setContent(snippet.content);
        setSelectedCategoryId(snippet.categoryId);
      } else {
        setName('');
        setContent('');
        setSelectedCategoryId(categoryId || 0);
      }
      setNameError('');
      setContentError('');
    }
  }, [open, snippet, categoryId]);
  
  const validateForm = () => {
    let isValid = true;
    
    // Validate name
    if (!name.trim()) {
      setNameError('Snippet name cannot be empty');
      isValid = false;
    } else if (name.length > 128) {
      setNameError('Snippet name must be 128 characters or fewer');
      isValid = false;
    } else if (!/^[\x00-\x7F]*$/.test(name)) { // Check if ASCII only
      setNameError('Snippet name must contain only ASCII characters');
      isValid = false;
    } else {
      setNameError('');
    }
    
    // Validate content
    if (!content.trim()) {
      setContentError('Snippet content cannot be empty');
      isValid = false;
    } else {
      setContentError('');
    }
    
    // Validate category
    if (!selectedCategoryId) {
      onError('Please select a category');
      isValid = false;
    }
    
    return isValid;
  };
  
  const handleSubmit = async (e) => {
    // Don't submit in read-only mode
    if (readOnly) {
      e.preventDefault();
      onClose();
      return;
    }
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSaving(true);
    
    try {
      let result;
      
      if (isEditMode) {
        // Update existing snippet
        const newCategoryId = selectedCategoryId !== snippet.categoryId ? selectedCategoryId : null;
        result = await updateSnippet(snippet.snippetId, name, content, newCategoryId);
      } else {
        // Create new snippet
        result = await addSnippet(selectedCategoryId, name, content);
      }
      
      if (result.ok) {
        onClose();
      } else {
        onError(result.error || 'Failed to save snippet');
      }
    } catch (error) {
      onError(error.message || 'An error occurred while saving the snippet');
    } finally {
      setIsSaving(false);
    }
  };
  
  return (
    <Dialog open={open} onClose={isSaving ? undefined : onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Snippet Name"
            fullWidth
            variant="outlined"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={Boolean(nameError)}
            helperText={nameError}
            disabled={isSaving || readOnly}
            inputProps={{ maxLength: 128 }}
            required
            sx={{ mb: 2 }}
          />
          
          {isEditMode && categories.length > 0 && (
            <FormControl fullWidth margin="dense" variant="outlined" sx={{ mb: 2 }}>
              <InputLabel>Category</InputLabel>
              <Select
                value={selectedCategoryId}
                onChange={(e) => setSelectedCategoryId(e.target.value)}
                label="Category"
                disabled={isSaving || readOnly}
              >
                {categories.map(cat => (
                  <MenuItem key={cat.categoryId} value={cat.categoryId}>
                    {cat.categoryName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          
          <TextField
            margin="dense"
            label="Content"
            fullWidth
            multiline
            rows={10}
            variant="outlined"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            error={Boolean(contentError)}
            helperText={contentError}
            disabled={isSaving || readOnly}
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button 
            type="submit" 
            variant="contained" 
            color="primary"
            disabled={isSaving || readOnly}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

SnippetEditorModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  categoryId: PropTypes.number,
  snippet: PropTypes.shape({
    snippetId: PropTypes.number.isRequired,
    categoryId: PropTypes.number.isRequired,
    snippetName: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired
  }),
  onError: PropTypes.func.isRequired,
  readOnly: PropTypes.bool
};

export default SnippetEditorModal;
