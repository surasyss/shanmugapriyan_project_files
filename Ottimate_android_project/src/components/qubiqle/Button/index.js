import React from 'react';
import { Text, TouchableOpacity } from 'react-native';
import styles from './styles';

export default function Button(props) {
  const {
    title, onPress, style
  } = props;
  let { type } = props;
  if (!type) {
    type = 'primary';
  }

  if (type === 'primary') {
    return (
      <TouchableOpacity style={{ ...styles.container, ...style }} onPress={onPress}>
        <Text style={styles.buttonText}>{title}</Text>
      </TouchableOpacity>
    );
  }
  if (type === 'outline') {
    return (
      <TouchableOpacity style={{ ...styles.outlineContainer, ...style }} onPress={onPress}>
        <Text style={styles.outlineButtonText}>{title}</Text>
      </TouchableOpacity>
    );
  }
  return null;
}
