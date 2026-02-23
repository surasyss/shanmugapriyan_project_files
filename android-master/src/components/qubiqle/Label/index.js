import React from 'react';
import { Text } from 'react-native';
import styles from './styles';

const Label = (props) => {
  const { title, style } = props;
  return (
    <Text style={[styles.flag, style]}>{title}</Text>
  );
};
export default Label;
