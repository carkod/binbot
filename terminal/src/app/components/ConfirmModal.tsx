import { useEffect, useState, type FC } from "react"
import { Button, Modal } from "react-bootstrap"

type ConfirmModalProps = {
  handleActions: (value: number) => void
  show: boolean
  primary?: string | JSX.Element
  secondary?: string | JSX.Element
  children?: React.ReactNode
}

const ConfirmModal: FC<ConfirmModalProps> = ({
  handleActions,
  show,
  secondary,
  primary,
  children,
}) => {
  const [toggle, setToggle] = useState(show)

  useEffect(() => {
    setToggle(show)
  }, [show])

  return (
    <Modal show={toggle} onHide={() => setToggle(false)} onEscapeKeyDown={() => setToggle(false)}>
      <Modal.Dialog className="border-0 my-0">
        <Modal.Header closeButton closeLabel="Cancel">Are you sure?</Modal.Header>
        <Modal.Body>{children}</Modal.Body>
        <Modal.Footer className="d-flex flex-row justify-content-between border border-bottom-0">
          <Button variant="danger" onClick={() => handleActions(1)}>
            {primary}
          </Button>
          <Button variant="warning" onClick={() => handleActions(2)}>
            {secondary}
          </Button>
        </Modal.Footer>
      </Modal.Dialog>
    </Modal>
  )
}

export default ConfirmModal
