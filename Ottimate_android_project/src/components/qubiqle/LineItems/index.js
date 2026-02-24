import React from 'react';
import { FlatList } from 'react-native';
import InvoiceEmpty from '../InvoiceEmpty';
import LineItem from '../LineItem';

export default function LineItems(props) {
  let { line_items } = props;
  if (!line_items) line_items = [];

  return (
    <FlatList
      data={line_items}
      renderItem={({ item, index }) => (
        <LineItem
          index={index}
          key={item.id.toString()}
          invoice={item}
        />
      )}
      ListHeaderComponent={line_items.length ? (
        <LineItem
          heading
          index={0}
        />
      ) : null}
      ListEmptyComponent={(
        <InvoiceEmpty
          message="There are no items to display"
        />
            )}
      keyExtractor={(item) => item.id.toString()}
      listKey={(item) => item.id.toString()}
    />
  );
}
