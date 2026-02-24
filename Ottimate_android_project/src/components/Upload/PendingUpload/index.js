import React from 'react';
import {
  Image, Text, View, TouchableOpacity
} from 'react-native';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import styles from './styles';
import { formatTakenAt } from '../../../utils/DateFormatter';
import PercentageLoader from '../../qubiqle/PercentageLoader';
import Colors from '../../../styles/Colors';

export default function PendingUpload(props) {
  let {
    uploadPercentage
  } = props;

  const {
    image, restaurant, takenAt, isCreated, onPress, invoice
  } = props;
  if (!uploadPercentage) uploadPercentage = 0;

  return (
    <TouchableOpacity
      style={styles.container}
      onPress={() => {
        if (onPress) {
          onPress(invoice);
        }
      }}
    >
      <View style={styles.leftView}>
        <Image
          source={{ uri: image }}
          style={styles.image}
        />

        <View>
          <Text style={styles.primaryText}>
            Taken At
            {' '}
            {formatTakenAt(takenAt)}
          </Text>
          <Text style={styles.secondaryText}>{restaurant ? restaurant.name : ''}</Text>
        </View>
      </View>

      <View>
        {isCreated
          ? (
            <Icon
              name="check-circle"
              style={styles.done}
            />
          ) : (
            <PercentageLoader
              radius={20}
              percent={uploadPercentage}
              color={Colors.primary}
              bgcolor={Colors.secondaryText}
            />
          )}
      </View>
    </TouchableOpacity>
  );
}
