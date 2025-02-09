import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { describe, it, expect, vi } from 'vitest';
import mockStore from '../../store/mockStore';
import BotsPage from '../Bots';
import { SpinnerContext } from '../../Layout';
import { BulkAction } from '../../components/BotsActions';

const store = mockStore();

const renderWithProviders = (ui, { store }) => {
  return render(
    <Provider store={store}>
      <SpinnerContext.Provider value={{ spinner: false, setSpinner: vi.fn() }}>
        {ui}
      </SpinnerContext.Provider>
    </Provider>
  );
};

describe('BotsPage', () => {
  it('renders BotsPage component', () => {
    renderWithProviders(<BotsPage />, { store });
    expect(screen.getByText(/Apply bulk action/i)).toBeInTheDocument();
  });

  it('handles bulk action selection', () => {
    renderWithProviders(<BotsPage />, { store });
    fireEvent.change(screen.getByLabelText(/Bulk Actions/i), {
      target: { value: BulkAction.SELECT_ALL },
    });
    fireEvent.click(screen.getByText(/Apply bulk action/i));
    expect(screen.getByText(/Apply bulk action/i)).toBeInTheDocument();
  });

  it('handles date filter changes', () => {
    renderWithProviders(<BotsPage />, { store });
    fireEvent.change(screen.getByLabelText(/Filter by start date/i), {
      target: { value: '2023-01-01' },
    });
    fireEvent.change(screen.getByLabelText(/Filter by end date/i), {
      target: { value: '2023-12-31' },
    });
    expect(screen.getByLabelText(/Filter by start date/i)).toHaveValue('2023-01-01');
    expect(screen.getByLabelText(/Filter by end date/i)).toHaveValue('2023-12-31');
  });

  it('handles bot deletion', () => {
    renderWithProviders(<BotsPage />, { store });
    fireEvent.click(screen.getByText(/Delete/i));
    expect(screen.getByText(/To close orders, please deactivate/i)).toBeInTheDocument();
  });
});
