/**
 * SnippetList Component - Displays and manages snippets for a selected category
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
  Tooltip,
  TextField,
  InputAdornment
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import PropTypes from 'prop-types';

/**
 * Renders a list of snippets with add, edit, delete, search functionality
 * @param {Object} props - Component props
 * @param {Array} props.snippets - List of snippet objects
 * @param {Function} props.onAdd - Handler for add snippet action
 * @param {Function} props.onEdit - Handler for edit snippet action
 * @param {Function} props.onDelete - Handler for delete snippet action
 * @param {Function} props.onView - Handler for viewing a snippet
 * @param {Function} props.onError - Handler for error reporting
 */
const SnippetList = ({
  snippets,
  onAdd,
  onEdit,
  onDelete,
  onView,
  onError
}) => {
  const [searchText, setSearchText] = React.useState('');

  // Filter snippets based on search text
  const filteredSnippets = React.useMemo(() => {
    if (!searchText) return snippets;

    const lowerSearch = searchText.toLowerCase();
    return snippets.filter(snippet =>
      snippet.snippetName.toLowerCase().includes(lowerSearch) ||
      snippet.content.toLowerCase().includes(lowerSearch)
    );
  }, [snippets, searchText]);

  return (
    <Paper elevation={0} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" component="h2">Snippets</Typography>
        <Tooltip title="Add Snippet">
          <IconButton
            color="primary"
            onClick={onAdd}
            aria-label="Add Snippet"
            disabled={!snippets || snippets.length === 0}
          >
            <AddIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Divider />

      {/* Search box */}
      <Box sx={{ p: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          size="small"
          placeholder="Search snippets..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <List sx={{ flexGrow: 1, overflow: 'auto' }}>
        {!snippets || snippets.length === 0 ? (
          <ListItem>
            <ListItemText primary="No snippets found. Select a category and add snippets." />
          </ListItem>
        ) : filteredSnippets.length === 0 ? (
          <ListItem>
            <ListItemText primary="No matching snippets found." />
          </ListItem>
        ) : (
          filteredSnippets.map(snippet => (
            <ListItem
              key={snippet.snippetId}
              button
              onClick={() => onView(snippet)}
            >
              <ListItemText
                primary={snippet.snippetName}
                secondary={snippet.content.length > 50
                  ? `${snippet.content.substring(0, 50)}...`
                  : snippet.content
                }
              />
              {onEdit && onDelete && (
                <ListItemSecondaryAction>
                  <Tooltip title="Edit Snippet">
                    <IconButton
                      edge="end"
                      aria-label="Edit"
                      onClick={() => onEdit(snippet)}
                      size="small"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete Snippet">
                    <IconButton
                      edge="end"
                      aria-label="Delete"
                      onClick={() => onDelete(snippet)}
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

SnippetList.propTypes = {
  snippets: PropTypes.arrayOf(PropTypes.shape({
    snippetId: PropTypes.number.isRequired,
    categoryId: PropTypes.number.isRequired,
    snippetName: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired
  })),
  onAdd: PropTypes.func.isRequired,
  onEdit: PropTypes.func,
  onDelete: PropTypes.func,
  onView: PropTypes.func,
  onError: PropTypes.func.isRequired
};

export default SnippetList;
