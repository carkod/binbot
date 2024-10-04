import type { FC } from "react"
import { Button, Modal } from "react-bootstrap"

type ConfirmModalProps = {
  modal: boolean
  handleActions: (value: number) => void
  close: boolean
  acceptText: string
  cancelText: string
  children: React.ReactNode
}

const ConfirmModal: FC<ConfirmModalProps> = ({
  modal,
  handleActions,
  close,
  acceptText,
  cancelText,
  children,
}) => {
  return (
    <Modal show={close} onHide={() => !!modal}>
      <Modal.Dialog>
        <Modal.Header>Are you sure?</Modal.Header>
        <Modal.Body>{children}</Modal.Body>
        <Modal.Footer>
          <Button variant="primary" onClick={() => handleActions(0)}>
            {acceptText}
          </Button>{" "}
          <Button variant="secondary" onClick={() => handleActions(1)}>
            {cancelText}
          </Button>
        </Modal.Footer>
      </Modal.Dialog>
    </Modal>
  )
}

export default ConfirmModal
