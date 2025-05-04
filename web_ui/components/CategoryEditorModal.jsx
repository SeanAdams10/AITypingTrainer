/**
 * CategoryEditorModal Component - Form dialog for adding/editing categories
 */
import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  TextField, 
  Button, 
  Typography 
} from '@mui/material';
import PropTypes from 'prop-types';
import { addCategory, updateCategory } from '../graphqlClient';

/**
 * Modal dialog for adding or editing a category
 * @param {Object} props - Component props
 * @param {boolean} props.open - Whether the dialog is open
 * @param {Function} props.onClose - Handler for dialog close
 * @param {Object} props.category - Category object (for edit mode, null for add mode)
 * @param {Function} props.onError - Handler for error reporting
 */
const CategoryEditorModal = ({ open, onClose, category, onError }) => {
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  
  // Reset form when dialog opens or category changes
  useEffect(() => {
    if (open) {
      setName(category ? category.categoryName : '');
      setNameError('');
    }
  }, [open, category]);
  
  const isEditMode = Boolean(category);
  const title = isEditMode ? 'Edit Category' : 'Add Category';
  
  const validateForm = () => {
    let isValid = true;
    
    // Validate name
    if (!name.trim()) {
      setNameError('Category name cannot be empty');
      isValid = false;
    } else if (name.length > 50) {
      setNameError('Category name must be 50 characters or fewer');
      isValid = false;
    } else if (!/^[\x00-\x7F]*$/.test(name)) { // Check if ASCII only
      setNameError('Category name must contain only ASCII characters');
      isValid = false;
    } else {
      setNameError('');
    }
    
    return isValid;
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSaving(true);
    
    try {
      let result;
      
      if (isEditMode) {
        // Update existing category
        result = await updateCategory(category.categoryId, name);
      } else {
        // Create new category
        result = await addCategory(name);
      }
      
      if (result.ok) {
        onClose();
      } else {
        onError(result.error || 'Failed to save category');
      }
    } catch (error) {
      onError(error.message || 'An error occurred while saving the category');
    } finally {
      setIsSaving(false);
    }
  };
  
  return (
    <Dialog open={open} onClose={isSaving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Category Name"
            fullWidth
            variant="outlined"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={Boolean(nameError)}
            helperText={nameError}
            disabled={isSaving}
            inputProps={{ maxLength: 50 }}
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
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

CategoryEditorModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  category: PropTypes.shape({
    categoryId: PropTypes.number.isRequired,
    categoryName: PropTypes.string.isRequired
  }),
  onError: PropTypes.func.isRequired
};

export default CategoryEditorModal;
