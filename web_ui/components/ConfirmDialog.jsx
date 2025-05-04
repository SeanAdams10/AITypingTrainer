/**
 * ConfirmDialog Component - Reusable confirmation dialog
 */
import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  Typography 
} from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Generic confirmation dialog component
 * @param {Object} props - Component props
 * @param {boolean} props.open - Whether the dialog is open
 * @param {Function} props.onClose - Handler for dialog close/cancel
 * @param {Function} props.onConfirm - Handler for confirm action
 * @param {string} props.title - Dialog title
 * @param {string} props.message - Confirmation message
 * @param {string} props.confirmButtonText - Text for the confirm button (default: "Confirm")
 * @param {string} props.cancelButtonText - Text for the cancel button (default: "Cancel")
 * @param {string} props.confirmButtonColor - Color for the confirm button (default: "error")
 */
const ConfirmDialog = ({ 
  open, 
  onClose, 
  onConfirm, 
  title = 'Confirm Action', 
  message = 'Are you sure you want to proceed?',
  confirmButtonText = 'Confirm',
  cancelButtonText = 'Cancel',
  confirmButtonColor = 'error'
}) => {
  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="sm"
    >
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Typography>{message}</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">
          {cancelButtonText}
        </Button>
        <Button 
          onClick={onConfirm} 
          variant="contained" 
          color={confirmButtonColor}
          autoFocus
        >
          {confirmButtonText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

ConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  title: PropTypes.string,
  message: PropTypes.string,
  confirmButtonText: PropTypes.string,
  cancelButtonText: PropTypes.string,
  confirmButtonColor: PropTypes.string
};

export default ConfirmDialog;
