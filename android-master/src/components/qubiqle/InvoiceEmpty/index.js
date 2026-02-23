import React from 'react';
import { Text, View } from 'react-native';
import styles from './styles';
import Loader from '../Loader';

export default function InvoiceEmpty(props) {
  let { message } = props;
  const { loading } = props;
  if (!message) message = 'Apply Filters to Browse Invoices';
  return (
    <View style={styles.container}>
      <Loader
        loading={loading}
      />
      <View style={styles.textParent}>
        <Text style={styles.text}>
          {message}
        </Text>
      </View>
    </View>
  );
}
