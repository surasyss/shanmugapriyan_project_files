import React, { Component } from 'react';
import Toast from '../../qubiqle/Toast';
import Colors from '../../../styles/Colors';

class ErrorToast extends Component {
  render() {
    return (
      <Toast
        ref={(ref) => {
          global.errorToast = ref;
        }}
        borderColor={Colors.red}
      />
    );
  }
}

export default ErrorToast;
