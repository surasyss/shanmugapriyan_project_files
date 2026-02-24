import React from 'react';
import {
  Text, TouchableOpacity, Image
} from 'react-native';
import styles from './styles';

export default function MoreSheetItem({ item }) {
  const {
    title, onPress, icon, cancel
  } = item;

  if (cancel) {
    return (
      <TouchableOpacity
        style={styles.container}
        key={title}
        onPress={() => onPress()}
      >
        <Text style={styles.cancel}>Cancel</Text>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      style={styles.container}
      key={title}
      onPress={() => onPress()}
    >
      <Image source={icon} style={styles.icon} resizeMode="contain" />
      <Text style={styles.title}>{title}</Text>
    </TouchableOpacity>
  );
}
