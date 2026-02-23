import React from 'react';
import {
  Image, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';
import Images from '../../../styles/Images';
import { filterCount } from '../../../utils/StringFormatter';

export default function CreditRequestFilterBar(props) {
  const {
    title, onSearch, onFilter, style, filters
  } = props;
  const count = filterCount(filters);

  return (
    <View style={[styles.container, style]}>
      <TouchableOpacity onPress={onFilter}>
        <Image
          source={Images.filter}
          style={styles.filter}
          resizeMode="contain"
        />
      </TouchableOpacity>
      {count !== 0
        ? (
          <View style={styles.filterCountParent}>
            <Text style={styles.filterCount}>{count}</Text>
          </View>
        )
        : null}

      <Text style={styles.title}>{title}</Text>
      <TouchableOpacity onPress={onSearch}>
        <Image
          source={Images.search}
          style={styles.search}
          resizeMode="contain"
        />
      </TouchableOpacity>
    </View>
  );
}
