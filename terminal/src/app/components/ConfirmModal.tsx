import { Button, Group, Modal } from "@mantine/core";
import type { ReactNode } from "react";

type ConfirmModalProps = {
  handleActions: (value: number) => void;
  show: boolean;
  onClose: () => void;
  primary?: ReactNode;
  secondary?: ReactNode;
  children?: ReactNode;
};

const ConfirmModal = ({
  handleActions,
  show,
  onClose,
  primary,
  secondary,
  children,
}: ConfirmModalProps) => {
  return (
    <Modal
      opened={show}
      onClose={onClose}
      title="Are you sure?"
      centered
      closeButtonProps={{ "aria-label": "Cancel" }}
    >
      {children}
      <Group justify="space-between" mt="lg">
        <Button color="danger" onClick={() => handleActions(1)}>
          {primary}
        </Button>
        {secondary && (
          <Button color="warning" onClick={() => handleActions(2)}>
            {secondary}
          </Button>
        )}
      </Group>
    </Modal>
  );
};

export default ConfirmModal;
