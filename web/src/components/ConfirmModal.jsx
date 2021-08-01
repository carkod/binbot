import React from 'react';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { checkValue } from '../validations';

const ConfirmModal = ({ modal, handleActions, close, acceptText, cancelText, children }) => {

  return (
    <div>
      <Modal toggle={close} isOpen={!checkValue(modal) ? true : false}>
        <ModalHeader toggle={close}>Are you sure?</ModalHeader>
        <ModalBody>
          {children}
        </ModalBody>
        <ModalFooter>
          <Button color="primary" onClick={() => handleActions(0)}>{acceptText}</Button>{' '}
          <Button color="secondary" onClick={() => handleActions(1)}>{cancelText}</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}

export default ConfirmModal;