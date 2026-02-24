import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import styles from './styles';

export default function Loader(props) {
  const { loading } = props;

  if (loading) {
    return (
      <ActivityIndicator
        style={styles.loading}
        size="small"
      />
    );
  }
  return <View />;
}
