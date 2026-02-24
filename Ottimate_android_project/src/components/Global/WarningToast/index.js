import React, { Component } from 'react';
import Toast from '../../qubiqle/Toast';
import Colors from '../../../styles/Colors';

class WarningToast extends Component {
  render() {
    return (
      <Toast
        ref={(ref) => {
          global.warningToast = ref;
        }}
        borderColor={Colors.warning}
      />
    );
  }
}

export default WarningToast;
