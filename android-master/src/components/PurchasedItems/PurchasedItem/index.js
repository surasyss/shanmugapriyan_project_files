import React from 'react';
import {
  Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

import { title } from '../../../utils/StringFormatter';

export default function PurchasedItem(props) {
  const {
    item, onPress, index
  } = props;

  if (item) {
    const {
      vendor_name
    } = item;
    let { name } = item;
    if (!name) name = '';
    name = name.trim();

    return (
      <TouchableOpacity
        style={styles.mainView}
        onPress={() => {
          if (onPress) {
            onPress(index);
          }
        }}
      >
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={[styles.itemName, name ? {} : styles.missing]}>{title(name) || '---'}</Text>
            <Text style={styles.secondaryText}>
              {vendor_name}
            </Text>
          </View>
        </View>

      </TouchableOpacity>
    );
  }
}
