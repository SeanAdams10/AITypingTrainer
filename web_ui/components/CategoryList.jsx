/**
 * CategoryList Component - Displays and manages categories
 */
import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Typography,
  Divider,
  Box,
  Paper,
  Tooltip
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import PropTypes from 'prop-types';

/**
 * Renders a list of categories with add, edit, delete actions
 * @param {Object} props - Component props
 * @param {Array} props.categories - List of category objects
 * @param {Object} props.selected - Currently selected category
 * @param {Function} props.onSelect - Handler for category selection
 * @param {Function} props.onAdd - Handler for add category action
 * @param {Function} props.onEdit - Handler for edit category action
 * @param {Function} props.onDelete - Handler for delete category action
 * @param {Function} props.onError - Handler for error reporting
 */
const CategoryList = ({
  categories,
  selected,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  onError
}) => {
  return (
    <Paper elevation={0} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" component="h2">Categories</Typography>
        <Tooltip title="Add Category">
          <IconButton
            color="primary"
            onClick={onAdd}
            aria-label="Add Category"
          >
            <AddIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Divider />
      <List sx={{ flexGrow: 1, overflow: 'auto' }}>
        {categories.length === 0 ? (
          <ListItem>
            <ListItemText primary="No categories found" />
          </ListItem>
        ) : (
          categories.map(category => (
            <ListItem
              key={category.categoryId}
              button
              selected={selected && selected.categoryId === category.categoryId}
              onClick={() => onSelect(category)}
            >
              <ListItemText primary={category.categoryName} />
              {onEdit && onDelete && (
                <ListItemSecondaryAction>
                  <Tooltip title="Edit Category">
                    <IconButton
                      edge="end"
                      aria-label="Edit"
                      onClick={() => onEdit(category)}
                      size="small"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete Category">
                    <IconButton
                      edge="end"
                      aria-label="Delete"
                      onClick={() => onDelete(category)}
                      size="small"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </ListItemSecondaryAction>
              )}
            </ListItem>
          ))
        )}
      </List>
    </Paper>
  );
};

CategoryList.propTypes = {
  categories: PropTypes.arrayOf(PropTypes.shape({
    categoryId: PropTypes.number.isRequired,
    categoryName: PropTypes.string.isRequired
  })).isRequired,
  selected: PropTypes.shape({
    categoryId: PropTypes.number.isRequired,
    categoryName: PropTypes.string.isRequired
  }),
  onSelect: PropTypes.func.isRequired,
  onAdd: PropTypes.func.isRequired,
  onEdit: PropTypes.func,
  onDelete: PropTypes.func,
  onError: PropTypes.func.isRequired
};

export default CategoryList;
