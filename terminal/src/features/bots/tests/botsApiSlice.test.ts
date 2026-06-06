import { singleBot } from "../botInitialState";
import { buildBotRequest } from "../botsApiSlice";

describe("buildBotRequest", () => {
  it("submits only editable recovery fields", () => {
    const request = buildBotRequest({
      ...singleBot,
      recovery_mode_id: "recovery-row-id",
      recovery_params: {
        id: "recovery-row-id",
        reversal_path: "recovery",
        source_contracts: 11,
        source_loss_fiat: 4.25,
        stop_loss_pct: 7.5,
        created_at: 100,
        updated_at: 200,
      },
    });

    expect(request).not.toHaveProperty("recovery_mode_id");
    expect(request.recovery_params).toEqual({
      reversal_path: "recovery",
      source_contracts: 11,
      source_loss_fiat: 4.25,
      stop_loss_pct: 7.5,
    });
  });

  it("preserves an explicit null recovery submission", () => {
    const request = buildBotRequest({
      ...singleBot,
      recovery_params: null,
    });

    expect(request.recovery_params).toBeNull();
  });

  it("omits undefined recovery params when serialized", () => {
    const request = buildBotRequest({
      ...singleBot,
      recovery_params: undefined,
    });
    const serializedRequest = JSON.parse(JSON.stringify(request));

    expect(serializedRequest).not.toHaveProperty("recovery_params");
  });
});
