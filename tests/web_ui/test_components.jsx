/**
 * Tests for React components for the Snippets Library Web UI
 * Using React Testing Library for component testing
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { act } from 'react-dom/test-utils';

// Import components to test
import CategoryList from '../../web_ui/components/CategoryList';
import SnippetList from '../../web_ui/components/SnippetList';
import CategoryEditorModal from '../../web_ui/components/CategoryEditorModal';
import SnippetEditorModal from '../../web_ui/components/SnippetEditorModal';
import ConfirmDialog from '../../web_ui/components/ConfirmDialog';

// Mock GraphQL client
jest.mock('../../web_ui/graphqlClient', () => ({
  fetchCategories: jest.fn(),
  fetchSnippets: jest.fn(),
  addCategory: jest.fn(),
  updateCategory: jest.fn(),
  deleteCategory: jest.fn(),
  addSnippet: jest.fn(),
  updateSnippet: jest.fn(),
  deleteSnippet: jest.fn(),
}));

describe('CategoryList Component', () => {
  const mockCategories = [
    { categoryId: 1, categoryName: 'Python' },
    { categoryId: 2, categoryName: 'JavaScript' }
  ];
  
  const mockProps = {
    categories: mockCategories,
    selected: null,
    onSelect: jest.fn(),
    onAdd: jest.fn(),
    onEdit: jest.fn(),
    onDelete: jest.fn(),
    onError: jest.fn()
  };
  
  test('renders category list', () => {
    render(<CategoryList {...mockProps} />);
    
    // Check header
    expect(screen.getByText('Categories')).toBeInTheDocument();
    
    // Check categories
    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('JavaScript')).toBeInTheDocument();
    
    // Check action buttons
    expect(screen.getByLabelText('Add Category')).toBeInTheDocument();
  });
  
  test('selects category on click', () => {
    render(<CategoryList {...mockProps} />);
    
    fireEvent.click(screen.getByText('Python'));
    expect(mockProps.onSelect).toHaveBeenCalledWith(mockCategories[0]);
  });
  
  test('calls onAdd when add button is clicked', () => {
    render(<CategoryList {...mockProps} />);
    
    fireEvent.click(screen.getByLabelText('Add Category'));
    expect(mockProps.onAdd).toHaveBeenCalled();
  });
});

describe('SnippetList Component', () => {
  const mockSnippets = [
    { 
      snippetId: 1, 
      categoryId: 1, 
      snippetName: 'Hello World', 
      content: 'print("Hello, World!")' 
    }
  ];
  
  const mockProps = {
    snippets: mockSnippets,
    onAdd: jest.fn(),
    onEdit: jest.fn(),
    onDelete: jest.fn(),
    onView: jest.fn(),
    onError: jest.fn()
  };
  
  test('renders snippet list', () => {
    render(<SnippetList {...mockProps} />);
    
    // Check header
    expect(screen.getByText('Snippets')).toBeInTheDocument();
    
    // Check snippets
    expect(screen.getByText('Hello World')).toBeInTheDocument();
    
    // Check action buttons
    expect(screen.getByLabelText('Add Snippet')).toBeInTheDocument();
  });
  
  test('calls onView when snippet is clicked', () => {
    render(<SnippetList {...mockProps} />);
    
    fireEvent.click(screen.getByText('Hello World'));
    expect(mockProps.onView).toHaveBeenCalledWith(mockSnippets[0]);
  });
  
  test('calls onAdd when add button is clicked', () => {
    render(<SnippetList {...mockProps} />);
    
    fireEvent.click(screen.getByLabelText('Add Snippet'));
    expect(mockProps.onAdd).toHaveBeenCalled();
  });
});

describe('CategoryEditorModal Component', () => {
  const mockProps = {
    open: true,
    onClose: jest.fn(),
    onSave: jest.fn(),
    onError: jest.fn(),
    category: null, // for add mode
  };
  
  test('renders add category form', () => {
    render(<CategoryEditorModal {...mockProps} />);
    
    // Check title
    expect(screen.getByText('Add Category')).toBeInTheDocument();
    
    // Check form controls
    expect(screen.getByLabelText('Category Name')).toBeInTheDocument();
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });
  
  test('renders edit category form', () => {
    const editProps = {
      ...mockProps,
      category: { categoryId: 1, categoryName: 'Python' }
    };
    
    render(<CategoryEditorModal {...editProps} />);
    
    // Check title
    expect(screen.getByText('Edit Category')).toBeInTheDocument();
    
    // Check form with prefilled value
    const input = screen.getByLabelText('Category Name');
    expect(input.value).toBe('Python');
  });
  
  test('calls onSave with form data', async () => {
    render(<CategoryEditorModal {...mockProps} />);
    
    // Fill the form
    const input = screen.getByLabelText('Category Name');
    fireEvent.change(input, { target: { value: 'TypeScript' } });
    
    // Submit the form
    fireEvent.click(screen.getByText('Save'));
    
    // Check if onSave was called with right data
    await waitFor(() => {
      expect(mockProps.onSave).toHaveBeenCalledWith({ categoryName: 'TypeScript' });
    });
  });
});

describe('SnippetEditorModal Component', () => {
  const mockProps = {
    open: true,
    onClose: jest.fn(),
    onSave: jest.fn(),
    onError: jest.fn(),
    categoryId: 1,
    snippet: null, // for add mode
  };
  
  test('renders add snippet form', () => {
    render(<SnippetEditorModal {...mockProps} />);
    
    // Check title
    expect(screen.getByText('Add Snippet')).toBeInTheDocument();
    
    // Check form controls
    expect(screen.getByLabelText('Snippet Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Content')).toBeInTheDocument();
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });
  
  test('renders edit snippet form', () => {
    const editProps = {
      ...mockProps,
      snippet: { 
        snippetId: 1, 
        categoryId: 1, 
        snippetName: 'Hello World', 
        content: 'print("Hello, World!")' 
      }
    };
    
    render(<SnippetEditorModal {...editProps} />);
    
    // Check title
    expect(screen.getByText('Edit Snippet')).toBeInTheDocument();
    
    // Check form with prefilled values
    const nameInput = screen.getByLabelText('Snippet Name');
    const contentInput = screen.getByLabelText('Content');
    expect(nameInput.value).toBe('Hello World');
    expect(contentInput.value).toBe('print("Hello, World!")');
  });
  
  test('calls onSave with form data', async () => {
    render(<SnippetEditorModal {...mockProps} />);
    
    // Fill the form
    const nameInput = screen.getByLabelText('Snippet Name');
    const contentInput = screen.getByLabelText('Content');
    
    fireEvent.change(nameInput, { target: { value: 'Test Snippet' } });
    fireEvent.change(contentInput, { target: { value: 'console.log("Test");' } });
    
    // Submit the form
    fireEvent.click(screen.getByText('Save'));
    
    // Check if onSave was called with right data
    await waitFor(() => {
      expect(mockProps.onSave).toHaveBeenCalledWith({
        categoryId: 1,
        snippetName: 'Test Snippet',
        content: 'console.log("Test");'
      });
    });
  });
});

describe('ConfirmDialog Component', () => {
  const mockProps = {
    open: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this item?'
  };
  
  test('renders confirmation dialog', () => {
    render(<ConfirmDialog {...mockProps} />);
    
    // Check title and message
    expect(screen.getByText('Confirm Delete')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument();
    
    // Check buttons
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });
  
  test('calls onConfirm when confirm button is clicked', () => {
    render(<ConfirmDialog {...mockProps} />);
    
    fireEvent.click(screen.getByText('Confirm'));
    expect(mockProps.onConfirm).toHaveBeenCalled();
  });
  
  test('calls onClose when cancel button is clicked', () => {
    render(<ConfirmDialog {...mockProps} />);
    
    fireEvent.click(screen.getByText('Cancel'));
    expect(mockProps.onClose).toHaveBeenCalled();
  });
});
