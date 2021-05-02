export const LOADING = "LOADING";

export function loading(state) {
  return {
    type: LOADING,
    loading: state
  };
}
