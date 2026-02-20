import React from 'react';
import { Box, Button, Divider, Grid, Paper, Stack, Typography } from '@mui/material';

// Placeholder UI scaffold reflecting the Keyset spec list-first layout.
// Hook into real data by replacing the mock lists with data fetched via adapters/use-cases.
const KeysetsPage: React.FC = () => {
  const mockKeysets = [
    { id: 'ks-1', name: 'Home Row', progression: 1 },
    { id: 'ks-2', name: 'Top Row', progression: 2 },
  ];

  const selected = mockKeysets[0];

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4" gutterBottom>
          Edit Keysets
        </Typography>
        <Typography variant="body1" color="text.secondary">
          List-first layout: keysets on the left, details on the right. Autosave and progression rules
          will be wired to the KeysetCollection use case and repository once data APIs are connected.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
            <Stack spacing={1}>
              <Typography variant="h6">Keysets</Typography>
              <Typography variant="body2" color="text.secondary">
                Drag-and-drop ordering to come; items show progression_order.
              </Typography>
              <Divider />
              {mockKeysets.map((ks) => (
                <Button
                  key={ks.id}
                  variant={ks.id === selected.id ? 'contained' : 'outlined'}
                  fullWidth
                  sx={{ justifyContent: 'space-between' }}
                  disabled
                >
                  <span>{ks.name}</span>
                  <Typography variant="caption" color="inherit">
                    #{ks.progression}
                  </Typography>
                </Button>
              ))}
              <Button variant="contained" disabled>
                Add Keyset (coming soon)
              </Button>
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
            <Stack spacing={2}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Typography variant="h6">Details</Typography>
                <Stack direction="row" spacing={1}>
                  <Button size="small" variant="outlined" disabled>
                    Promote (Ctrl+Up)
                  </Button>
                  <Button size="small" variant="outlined" disabled>
                    Demote (Ctrl+Down)
                  </Button>
                </Stack>
              </Box>
              <Typography variant="body1" fontWeight={600}>
                {selected.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Progression order: {selected.progression}
              </Typography>
              <Divider />
              <Typography variant="subtitle1">Keys</Typography>
              <Typography variant="body2" color="text.secondary">
                Keys will appear here with mastered/current grouping per spec. Add/remove/move will be
                validated via KeysetCollection (progressive uniqueness, duplicate prompts, and autosave debounce).
              </Typography>
              <Stack direction="row" spacing={1}>
                <Button variant="contained" disabled>
                  Add Key (coming soon)
                </Button>
                <Button variant="outlined" disabled>
                  Remove Key (coming soon)
                </Button>
              </Stack>
              <Divider />
              <Typography variant="body2" color="text.secondary">
                Autosave: pending. Will debounce and show overlay while persisting. Errors from
                KeysetValidationError will surface as inline banners.
              </Typography>
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </Stack>
  );
};

export default KeysetsPage;
