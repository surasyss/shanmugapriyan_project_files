import React, { Component } from 'react';
import Toast from '../../qubiqle/Toast';
import Colors from '../../../styles/Colors';

class SimpleToast extends Component {
  render() {
    return (
      <Toast
        ref={(ref) => {
          global.toast = ref;
        }}
        borderColor={Colors.primary}
      />
    );
  }
}

export default SimpleToast;
