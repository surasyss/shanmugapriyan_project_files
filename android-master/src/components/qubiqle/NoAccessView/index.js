import React from 'react';
import { View, Text } from 'react-native';
import styles from './styles';

const NoAccessView = () => (
  <View style={styles.emptyContainer}>
    <Text style={styles.emptyMessage}>
      Access Restricted
    </Text>
  </View>
);

export default NoAccessView;
