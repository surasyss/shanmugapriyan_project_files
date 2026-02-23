import React, { Component } from 'react';
import Toast from '../../qubiqle/Toast';
import Colors from '../../../styles/Colors';

class SuccessToast extends Component {
  render() {
    return (
      <Toast
        ref={(ref) => {
          global.successToast = ref;
        }}
        borderColor={Colors.success}
      />
    );
  }
}

export default SuccessToast;
