import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardActions,
  CardContent,
  Grid,
  Link,
  Typography,
  Button,
} from '@mui/material';

const MENU_ITEMS = [
  { label: 'Manage Your Library of Text', route: null },
  { label: 'Do a Typing Drill', route: null },
  { label: 'Practice Weak Points', route: null },
  { label: 'Games', route: null },
  { label: 'View Last Progress', route: null },
  { label: 'N-gram Speed Heatmap', route: null },
  { label: 'Data Management', route: null },
  { label: 'View DB Content', route: null },
  { label: 'Query the DB', route: null },
  { label: 'Manage Users & Keyboards', route: null },
  { label: 'Edit Keysets', route: '/keysets' },
  { label: 'Quit Application', route: null },
];

const MainMenu: React.FC = () => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box>
        <Typography variant="h4" gutterBottom>Welcome</Typography>
        <Typography variant="body1" color="text.secondary">
          Mirror of the desktop main menu. Only "Edit Keysets" is active in this web build; other entries
          are shown for parity and will be enabled as their web features land.
        </Typography>
      </Box>
      <Grid container spacing={2}>
        {MENU_ITEMS.map((item) => {
          const isActive = Boolean(item.route);
          return (
            <Grid item xs={12} sm={6} md={4} key={item.label}>
              <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" gutterBottom>
                    {item.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {isActive ? 'Open this section' : 'Coming soon on the web'}
                  </Typography>
                </CardContent>
                <CardActions>
                  {isActive ? (
                    <Button
                      fullWidth
                      component={RouterLink}
                      to={item.route as string}
                      variant="contained"
                    >
                      Open
                    </Button>
                  ) : (
                    <Button fullWidth variant="outlined" disabled>
                      Coming soon
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          );
        })}
      </Grid>
      <Box>
        <Typography variant="body2" color="text.secondary">
          Desktop menu reference preserved for consistency. Navigation uses React Router for future URL-based pages.
        </Typography>
        <Link component={RouterLink} to="/keysets" underline="hover">
          Jump to Keysets
        </Link>
      </Box>
    </Box>
  );
};

export default MainMenu;
